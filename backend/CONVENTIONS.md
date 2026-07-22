# Backend conventions

Patterns this codebase expects new backend code to follow. See the root [README.md](../README.md) for what the app does and how to run it; this file is about how it's built.

## Errors

- Two exception types, one handler (see `main.py`): `PdnsError` (`core/pdns.py`) for anything that reaches PowerDNS — client-attributable statuses (`400`/`404`/`409`/`422`) pass through unchanged, everything else (auth/config problems, network failures) surfaces as `502`. `PolicyError` is for policy enforced locally, before PowerDNS is ever called (zone protection, auth). Same `{detail, code}` response shape for both, so the frontend doesn't need to know which one it hit, but the distinction stays available if it ever needs to branch.
- Every raised error carries a stable, machine-readable `code` (`zone_protected`, `zone_exists`, `zone_not_found`, `invalid_zone_name`, `not_authenticated`, `auth_not_configured`, `pdns_error`, `pdns_unavailable`). Add a new code for a new failure mode rather than overloading an existing one.

## Auth

- Zone/record data sits behind `Depends(require_auth)` for every verb, `GET` included (`list_zones`, `get_zone`), not just mutations — the interactive Scalar docs (`/api/scalar`) make anonymous browsing trivially discoverable, so read access is no longer left open. `GET /health` is the one deliberate exception: it's a liveness probe (Docker healthcheck calls it with no credentials) that reveals no DNS data.
- Auth fails closed: OIDC settings unset on the backend → `503 auth_not_configured`, never silently open.
- JWKS fetching goes through `JwksCache` (`core/auth.py`, httpx-based), not PyJWT's bundled `PyJWKClient` — that one fetches via `urllib`, which is invisible to `respx` in tests and blocks the event loop inside an async dependency.

## Zone-name handling

- Every zone/record name is canonicalized (`canonicalize`/`canonical_zone` in `core/pdns.py`) before any protection check runs — comparisons against `PROTECTED_ZONES` always happen on the canonical, lowercased, trailing-dot form, so a Unicode homoglyph or case variation can't slip past the guard.
- Zone name validation (LDH labels only, ≤253 octets, punycode for internationalized names) happens locally rather than relying on PowerDNS's error messages — PowerDNS's parse errors for bad names are unhelpful, and policy needs to inspect the name anyway to enforce zone protection.

## Zone protection

`ensure_zone_mutable`, `ensure_zone_creatable`, and `_ensure_apex_ns_mutable` (`core/pdns.py` / `api/routes.py`) are the only places zone protection is enforced. Any new zone- or record-level mutation must call the matching guard rather than re-implementing the check.

| Operation | Protected zone | Subzone of a protected zone | Any other zone |
|---|---|---|---|
| Delete the zone | 403 | 403 (a delegated child is part of the protected estate) | 204 |
| Create a zone with that name | 409 (already exists, from PowerDNS) | 403 (would shadow the parent) | 201 |
| Edit/delete an ordinary record | allowed — this is the tool's core purpose | allowed | allowed |
| Edit/delete the apex `NS` rrset | 403 (rewriting it is functionally zone destruction) | allowed (a subzone's own apex NS is a normal delegation record) | allowed |

Creating the *parent* of a protected zone is allowed: on the same authoritative server, queries for the child resolve against the more specific zone, so a parent can never shadow it.

## API docs

- Interactive docs (Scalar) live at `/api/scalar`, backed by `/api/openapi.json` — both replace FastAPI's default `/docs`/`/redoc`/`/openapi.json` (disabled via `FastAPI(openapi_url=None, docs_url=None, redoc_url=None)` in `main.py`) and both are gated dev-only by `_require_development` (`api/routes.py`), which reads `ENVIRONMENT` live at request time — same convention as `/health` — so no rebuild/restart is needed to flip them off.
- Endpoint/model docstrings are not just internal comments here: FastAPI surfaces them as the OpenAPI operation/schema descriptions Scalar renders. Add one to any new endpoint or response model, written for an API consumer reading generated docs, not a code reviewer.
- Scalar's "Authorize" button is prefilled for Keycloak OAuth2 (Authorization Code + PKCE), reusing the same public SPA client the frontend logs in with (`Settings.oidc_client_id`, `vendors/keycloak/realm-export.json`) — no separate Keycloak client for docs-only use.

## Testing

Backend tests always mock PowerDNS with `respx` (`tests/conftest.py`'s `pdns_mock` fixture) — no live DNS server in CI. A new endpoint that isn't supposed to touch PowerDNS needs a test asserting it makes zero calls to the mock (see `test_health_does_not_call_pdns`), not just a happy-path test.
