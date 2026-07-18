import jwt as pyjwt

from tests.conftest import KEY_ID, OIDC_JWKS_URL, ZONES_PATH, auth_headers, mint_token

ZONE_PATH = f"{ZONES_PATH}/example.test."
UPSERT_BODY = {"name": "web", "type": "A", "ttl": 300, "records": ["192.168.0.10"]}


def _put_record(client, headers: dict | None = None):
    return client.put("/api/zones/example.test./records", json=UPSERT_BODY, headers=headers)


def test_get_zones_succeeds_with_no_auth_header(client, pdns_mock) -> None:
    """Reads stay anonymous even with auth configured."""
    pdns_mock.get(ZONES_PATH).respond(200, json=[])
    response = client.get("/api/zones")
    assert response.status_code == 200


def test_mutation_without_header_is_401(client, pdns_mock) -> None:
    response = _put_record(client)
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_mutation_with_garbage_token_is_401(client, pdns_mock) -> None:
    response = _put_record(client, {"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_mutation_with_expired_token_is_401(client, pdns_mock) -> None:
    response = _put_record(client, auth_headers(exp=0))
    assert response.status_code == 401


def test_mutation_with_wrong_issuer_is_401(client, pdns_mock) -> None:
    response = _put_record(client, auth_headers(iss="http://evil.test/realms/other"))
    assert response.status_code == 401


def test_mutation_with_wrong_audience_is_401(client, pdns_mock) -> None:
    response = _put_record(client, auth_headers(aud="some-other-api"))
    assert response.status_code == 401


def test_mutation_with_alg_none_token_is_401(client, pdns_mock) -> None:
    response = _put_record(client, auth_headers(alg="none"))
    assert response.status_code == 401


def test_mutation_with_hs256_confusion_token_is_401(client, pdns_mock) -> None:
    """Reusing the real RS256 key's kid but signing with HS256 must not verify."""
    response = _put_record(client, auth_headers(alg="HS256"))
    assert response.status_code == 401


def test_mutation_with_unknown_kid_refetches_then_401(client, pdns_mock) -> None:
    """A kid outside the cached set triggers a refetch (in case of key rotation),
    not an immediate rejection — then a still-missing kid is a genuine 401."""
    pdns_mock.patch(ZONE_PATH).respond(204)
    first = _put_record(client, auth_headers())  # warms the cache with one fetch
    assert first.status_code == 200, first.text

    second = _put_record(client, auth_headers(kid="some-other-key"))
    assert second.status_code == 401

    jwks_calls = [c for c in pdns_mock.calls if c.request.url == OIDC_JWKS_URL]
    assert len(jwks_calls) == 2


def test_mutation_with_valid_token_succeeds(client, pdns_mock) -> None:
    pdns_mock.patch(ZONE_PATH).respond(204)
    response = _put_record(client, auth_headers())
    assert response.status_code == 200, response.text


def test_mutation_without_oidc_settings_is_503(client_no_auth, pdns_mock) -> None:
    response = _put_record(client_no_auth, auth_headers())
    assert response.status_code == 503
    assert response.json()["code"] == "auth_not_configured"


def test_valid_token_carries_expected_kid(client, pdns_mock) -> None:
    """Sanity check on the test fixture itself: mint_token signs with the JWKS's kid."""
    header = pyjwt.get_unverified_header(mint_token())
    assert header["kid"] == KEY_ID
