import json

import pytest

from tests.conftest import OIDC_JWKS_URL, ZONES_PATH, auth_headers

ZONE_PATH = f"{ZONES_PATH}/example.test."
LONG_ZONE = ".".join(["a" * 63] * 4) + ".test."  # valid per-label, exceeds 253 octets overall


def _pdns_calls(router) -> list:
    """pdns_mock.calls minus the JWKS fetch require_auth makes on every mutation."""
    return [c for c in router.calls if c.request.url != OIDC_JWKS_URL]


# --- create ---


def test_create_zone_canonicalizes_and_creates(client, pdns_mock) -> None:
    route = pdns_mock.post(ZONES_PATH).respond(
        201, json={"id": "lab.test.", "name": "lab.test.", "kind": "Native", "serial": 0}
    )
    response = client.post("/api/zones", json={"name": "LAB.TEST"}, headers=auth_headers())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "lab.test."
    assert body["protected"] is False
    payload = json.loads(route.calls.last.request.content)
    assert payload == {
        "name": "lab.test.",
        "kind": "Native",
        "soa_edit_api": "DEFAULT",
        "nameservers": ["ns1.example.test."],
    }


def test_create_zone_requires_auth(client, pdns_mock) -> None:
    response = client.post("/api/zones", json={"name": "lab.test"})
    assert response.status_code == 401
    assert not _pdns_calls(pdns_mock)


def test_create_zone_duplicate_maps_to_zone_exists(client, pdns_mock) -> None:
    pdns_mock.post(ZONES_PATH).respond(409, json={"error": "Zone already exists"})
    response = client.post("/api/zones", json={"name": "example.test."}, headers=auth_headers())
    assert response.status_code == 409
    assert response.json()["code"] == "zone_exists"


def test_create_zone_rejects_empty_name_at_the_shape_layer(client, pdns_mock) -> None:
    """Unlike a record name, "" has no apex-equivalent meaning for a zone: it's
    rejected by ZoneCreate's min_length=1 before reaching validate_zone_name,
    so it never gets the invalid_zone_name code — that's expected, not a gap."""
    response = client.post("/api/zones", json={"name": ""}, headers=auth_headers())
    assert response.status_code == 422
    assert not _pdns_calls(pdns_mock)


@pytest.mark.parametrize(
    "name",
    [
        " ",
        "-bad.test.",
        "bad-.test.",
        "bad_label.test.",
        "exämple.test.",  # raw Unicode: must be punycode
        "a" * 64 + ".test.",  # label over 63 octets
        LONG_ZONE,  # total over 253 octets
    ],
)
def test_create_zone_rejects_bad_names(client, pdns_mock, name) -> None:
    response = client.post("/api/zones", json={"name": name}, headers=auth_headers())
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_zone_name"
    assert not _pdns_calls(pdns_mock)


def test_create_zone_allows_single_label(client, pdns_mock) -> None:
    """Homelabs really use bare TLD-style zones like 'lan.'."""
    pdns_mock.post(ZONES_PATH).respond(
        201, json={"id": "lan.", "name": "lan.", "kind": "Native", "serial": 0}
    )
    response = client.post("/api/zones", json={"name": "lan"}, headers=auth_headers())
    assert response.status_code == 201, response.text


def test_create_zone_allows_punycode(client, pdns_mock) -> None:
    pdns_mock.post(ZONES_PATH).respond(
        201,
        json={
            "id": "xn--exmple-cua.test.",
            "name": "xn--exmple-cua.test.",
            "kind": "Native",
            "serial": 0,
        },
    )
    response = client.post(
        "/api/zones", json={"name": "xn--exmple-cua.test."}, headers=auth_headers()
    )
    assert response.status_code == 201, response.text


def test_create_subzone_of_protected_is_403(client, pdns_mock) -> None:
    """A shadowing child is a zone-level attack on the parent in every way that matters."""
    response = client.post(
        "/api/zones", json={"name": "evil.example.test."}, headers=auth_headers()
    )
    assert response.status_code == 403
    assert response.json()["code"] == "zone_protected"
    assert not _pdns_calls(pdns_mock)


def test_create_parent_of_protected_is_allowed(client, pdns_mock) -> None:
    """A parent doesn't shadow a more-specific child on the same authoritative server."""
    pdns_mock.post(ZONES_PATH).respond(
        201, json={"id": "test.", "name": "test.", "kind": "Native", "serial": 0}
    )
    response = client.post("/api/zones", json={"name": "test."}, headers=auth_headers())
    assert response.status_code == 201, response.text


# --- delete ---


def test_delete_unprotected_zone_succeeds(client, pdns_mock) -> None:
    pdns_mock.delete(f"{ZONES_PATH}/other.test.").respond(204)
    response = client.delete("/api/zones/other.test.", headers=auth_headers())
    assert response.status_code == 204


def test_delete_protected_zone_is_403(client, pdns_mock) -> None:
    response = client.delete("/api/zones/example.test.", headers=auth_headers())
    assert response.status_code == 403
    assert response.json()["code"] == "zone_protected"
    assert not _pdns_calls(pdns_mock)


def test_delete_subzone_of_protected_is_403(client, pdns_mock) -> None:
    """A delegated child is part of the protected estate; removed the way it was provisioned."""
    response = client.delete("/api/zones/child.example.test.", headers=auth_headers())
    assert response.status_code == 403
    assert not _pdns_calls(pdns_mock)


def test_delete_requires_auth(client, pdns_mock) -> None:
    response = client.delete("/api/zones/other.test.")
    assert response.status_code == 401
    assert not _pdns_calls(pdns_mock)


@pytest.mark.parametrize("zone_id", ["EXAMPLE.TEST", "example.test", "Example.Test."])
def test_delete_protected_zone_name_form_matrix(client, pdns_mock, zone_id) -> None:
    response = client.delete(f"/api/zones/{zone_id}", headers=auth_headers())
    assert response.status_code == 403
    assert not _pdns_calls(pdns_mock)


def test_delete_not_found_maps_to_zone_not_found(client, pdns_mock) -> None:
    pdns_mock.delete(f"{ZONES_PATH}/nope.test.").respond(404, json={"error": "Not Found"})
    response = client.delete("/api/zones/nope.test.", headers=auth_headers())
    assert response.status_code == 404
    assert response.json()["code"] == "zone_not_found"


# --- apex NS guard on record routes ---

APEX_NS_BODY = {"name": "@", "type": "NS", "ttl": 3600, "records": ["ns1.example.test."]}


@pytest.mark.parametrize("name_form", ["@", "", "example.test", "example.test."])
def test_apex_ns_edit_in_protected_zone_is_403(client, pdns_mock, name_form) -> None:
    response = client.put(
        "/api/zones/example.test./records",
        json={**APEX_NS_BODY, "name": name_form},
        headers=auth_headers(),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "zone_protected"
    assert not _pdns_calls(pdns_mock)


def test_apex_ns_delete_in_protected_zone_is_403(client, pdns_mock) -> None:
    response = client.delete(
        "/api/zones/example.test./records?name=@&type=NS", headers=auth_headers()
    )
    assert response.status_code == 403
    assert not _pdns_calls(pdns_mock)


def test_apex_ns_create_in_protected_zone_is_403(client, pdns_mock) -> None:
    response = client.post(
        "/api/zones/example.test./records", json=APEX_NS_BODY, headers=auth_headers()
    )
    assert response.status_code == 403
    assert not _pdns_calls(pdns_mock)


def test_apex_ns_edit_in_unprotected_zone_succeeds(client, pdns_mock) -> None:
    pdns_mock.patch(f"{ZONES_PATH}/other.test.").respond(204)
    response = client.put(
        "/api/zones/other.test./records", json=APEX_NS_BODY, headers=auth_headers()
    )
    assert response.status_code == 200, response.text


def test_non_apex_ns_edit_in_protected_zone_succeeds(client, pdns_mock) -> None:
    """Delegation NS records for a subzone are a normal, non-apex operation."""
    pdns_mock.patch(ZONE_PATH).respond(204)
    response = client.put(
        "/api/zones/example.test./records",
        json={"name": "delegated", "type": "NS", "ttl": 3600, "records": ["ns1.example.test."]},
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
