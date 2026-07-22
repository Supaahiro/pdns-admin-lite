def test_scalar_docs_available_in_development(client, pdns_mock, monkeypatch) -> None:
    """The Scalar UI is reachable when ENVIRONMENT is unset/DEVELOPMENT, with zero PowerDNS calls."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    response = client.get("/api/scalar")
    assert response.status_code == 200
    assert not pdns_mock.calls


def test_openapi_json_available_in_development(client, pdns_mock, monkeypatch) -> None:
    """The schema backing Scalar is reachable in dev, with zero PowerDNS calls."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "pdns-admin-lite"
    assert not pdns_mock.calls


def test_scalar_docs_hidden_outside_development(client, pdns_mock, monkeypatch) -> None:
    """Flipping ENVIRONMENT away from DEVELOPMENT 404s the docs UI."""
    monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
    response = client.get("/api/scalar")
    assert response.status_code == 404
    assert not pdns_mock.calls


def test_openapi_json_hidden_outside_development(client, pdns_mock, monkeypatch) -> None:
    """Flipping ENVIRONMENT away from DEVELOPMENT 404s the schema too."""
    monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
    response = client.get("/api/openapi.json")
    assert response.status_code == 404
    assert not pdns_mock.calls
