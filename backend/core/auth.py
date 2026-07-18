"""JWT verification for the Keycloak-issued access tokens the SPA sends.

PyJWT does the crypto; JwksCache is a small httpx-based replacement for
PyJWT's bundled PyJWKClient, which fetches keys via urllib (invisible to
respx, breaking the "no live Keycloak in tests" constraint) and blocks the
event loop inside an async dependency.
"""

import time

import httpx
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from core.pdns import PolicyError

JWKS_TTL_SECONDS = 3600
CLOCK_SKEW_LEEWAY_SECONDS = 30

_bearer = HTTPBearer(auto_error=False)


class Claims(BaseModel):
    sub: str
    preferred_username: str


class JwksCache:
    """Fetches the JWKS via httpx; caches keys by kid; refetches when a kid
    is unknown or the cache is older than JWKS_TTL_SECONDS. Not data — a
    performance detail, not state that needs to survive a restart.
    """

    def __init__(self, http: httpx.AsyncClient, url: str) -> None:
        self._http = http
        self._url = url
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float = 0.0

    async def get_key(self, kid: str) -> jwt.PyJWK:
        if kid not in self._keys or self._is_stale():
            await self._refresh()
        try:
            return self._keys[kid]
        except KeyError:
            raise jwt.InvalidTokenError(f"Unknown key id: {kid}") from None

    def _is_stale(self) -> bool:
        return time.monotonic() - self._fetched_at > JWKS_TTL_SECONDS

    async def _refresh(self) -> None:
        resp = await self._http.get(self._url)
        resp.raise_for_status()
        jwk_set = jwt.PyJWKSet.from_dict(resp.json())
        self._keys = {key.key_id: key for key in jwk_set.keys if key.key_id}
        self._fetched_at = time.monotonic()


def _jwks_cache(request: Request) -> JwksCache:
    cache: JwksCache | None = getattr(request.app.state, "jwks_cache", None)
    if cache is None:
        settings = request.app.state.settings
        cache = JwksCache(request.app.state.oidc_http, settings.oidc_jwks_url)
        request.app.state.jwks_cache = cache
    return cache


async def require_auth(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Claims:
    settings = request.app.state.settings
    if not (settings.oidc_issuer and settings.oidc_jwks_url and settings.oidc_audience):
        raise PolicyError(503, "Authentication is not configured", code="auth_not_configured")
    if creds is None:
        raise PolicyError(401, "Authentication required", code="not_authenticated")

    try:
        header = jwt.get_unverified_header(creds.credentials)
        key = await _jwks_cache(request).get_key(header["kid"])
        payload = jwt.decode(
            creds.credentials,
            key=key.key,
            algorithms=["RS256"],
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            leeway=CLOCK_SKEW_LEEWAY_SECONDS,
        )
    except (jwt.PyJWTError, KeyError, httpx.HTTPError) as exc:
        raise PolicyError(401, f"Invalid token: {exc}", code="not_authenticated") from exc

    return Claims(
        sub=payload["sub"],
        preferred_username=payload.get("preferred_username", payload["sub"]),
    )
