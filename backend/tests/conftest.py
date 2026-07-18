import time

import jwt as pyjwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from core.config import Settings
from main import build_app

PDNS_BASE = "http://pdns.test/api/v1"
ZONES_PATH = "/servers/localhost/zones"

OIDC_ISSUER = "http://keycloak.test/realms/pdns-admin-lite"
OIDC_JWKS_URL = "http://keycloak.test/realms/pdns-admin-lite/protocol/openid-connect/certs"
OIDC_AUDIENCE = "pdns-admin-lite-api"
KEY_ID = "test-key-1"

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks_body() -> dict:
    jwk = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
    jwk.update(kid=KEY_ID, use="sig", alg="RS256")
    return {"keys": [jwk]}


def mint_token(*, alg: str = "RS256", kid: str | None = KEY_ID, **claim_overrides) -> str:
    """Signs a JWT with the test RSA key; defaults describe a valid demo-user token.

    `alg`/`kid` let tests build the attack shapes require_auth must reject:
    alg="none" or alg="HS256" (with the real kid) probe the algorithm
    allow-list; kid="unknown" probes the refetch-then-fail path.
    """
    now = int(time.time())
    claims = {
        "iss": OIDC_ISSUER,
        "aud": OIDC_AUDIENCE,
        "sub": "demo-user-id",
        "preferred_username": "demo",
        "iat": now,
        "exp": now + 300,
        **claim_overrides,
    }
    headers = {"kid": kid} if kid else {}
    key = _PRIVATE_KEY if alg not in ("none", "HS256") else (None if alg == "none" else "x" * 32)
    return pyjwt.encode(claims, key, algorithm=alg, headers=headers)


def auth_headers(**claim_overrides) -> dict:
    return {"Authorization": f"Bearer {mint_token(**claim_overrides)}"}


@pytest.fixture
def pdns_mock():
    """Mock router intercepting the app's outbound calls to PowerDNS and Keycloak.

    respx only patches httpx's default transports, so the TestClient's own
    ASGI transport is unaffected. assert_all_called is off: several tests
    exercise early-exit auth failures that never reach a registered route by
    design; `pdns_mock.calls` assertions cover the on-purpose checks.
    """
    with respx.mock(base_url=PDNS_BASE, assert_all_called=False) as router:
        yield router


@pytest.fixture
def client(pdns_mock):
    pdns_mock.get(OIDC_JWKS_URL).respond(200, json=_jwks_body())
    app = build_app(
        Settings(
            pdns_api_url=PDNS_BASE,
            pdns_api_key="test-key",
            oidc_issuer=OIDC_ISSUER,
            oidc_jwks_url=OIDC_JWKS_URL,
            oidc_audience=OIDC_AUDIENCE,
        )
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_no_auth(pdns_mock):
    """A client with OIDC settings unset, for the fail-closed 503 path."""
    app = build_app(Settings(pdns_api_url=PDNS_BASE, pdns_api_key="test-key"))
    with TestClient(app) as test_client:
        yield test_client
