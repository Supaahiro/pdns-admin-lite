"""Application settings, loaded from environment variables (and .env in local dev)."""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from core.pdns import canonical_zone


class Settings(BaseSettings):
    """Runtime configuration for the PowerDNS adapter.

    Every field has a default so importing the app never fails; real values
    come from the environment (PDNS_API_URL, PDNS_API_KEY, ...).
    """

    pdns_api_url: str = "http://pdns:8081/api/v1"
    pdns_api_key: str = ""
    pdns_server_id: str = "localhost"
    cors_origins: list[str] = []

    # Empty by default: unset means auth is not configured, and require_auth
    # fails closed (503) rather than silently accepting unverifiable tokens.
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""
    # Public SPA client (see vendors/keycloak/realm-export.json), reused to
    # prefill the Scalar docs' OAuth2/PKCE login — not used for JWT
    # verification, only for the dev-docs "Authorize" button.
    oidc_client_id: str = "pdns-admin-lite-spa"

    # Comma-separated zone names, canonicalized at load time. Never
    # deletable/zone-modifiable regardless of who is authenticated. NoDecode:
    # pydantic-settings otherwise JSON-decodes complex-typed env vars before
    # any field validator runs, rejecting a plain comma-separated string.
    protected_zones: Annotated[set[str], NoDecode] = {"example.test."}
    default_ns: str = "ns1.example.test."

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("protected_zones", mode="before")
    @classmethod
    def _parse_protected_zones(cls, value: object) -> object:
        if isinstance(value, str):
            return {canonical_zone(entry) for entry in value.split(",") if entry.strip()}
        if isinstance(value, (list, set, tuple)):
            return {canonical_zone(entry) for entry in value}
        return value
