# pdns-admin-lite

[![release](https://github.com/Supaahiro/pdns-admin-lite/actions/workflows/release.yml/badge.svg)](https://github.com/Supaahiro/pdns-admin-lite/actions/workflows/release.yml)

A minimal web UI for managing DNS zones and records on a **PowerDNS Authoritative** server. It consists of a **FastAPI** backend, a **Vue** 3 frontend, and a **Caddy** reverse proxy, all orchestrated with **Docker Compose**.

> Scope: the application manages only the zones it owns. Zones listed in `PROTECTED_ZONES` (and their subzones) are always read-only and cannot be modified or deleted through the UI.

```mermaid
flowchart LR
    browser(["Browser"]) --> edge

    subgraph stack["docker compose"]
        edge["edge<br/>Caddy :8080"]
        frontend["frontend<br/>nginx :80"]
        backend["backend<br/>FastAPI :8000"]
        pdns["pdns<br/>PowerDNS API :8081"]
        seed["pdns-seed<br/>(one-shot)"]
        keycloak["keycloak<br/>:8080 (/auth)"]
    end

    edge -->|"/api/*"| backend
    edge -->|"/auth/*"| keycloak
    edge -->|"/auth/admin/*"| blocked(["403"])
    edge -->|"/* (everything else)"| frontend
    backend -->|"REST"| pdns
    backend -.->|"JWKS"| keycloak
    seed -->|"seeds example.test."| pdns
```

---

## Key Features

- 🌐 Manage PowerDNS zones and DNS records through a simple web UI
- ✏️ Create, edit and delete common DNS record types (`A`, `AAAA`, `CNAME`, `TXT`, `MX`, `SRV`, `NS`, `PTR`)
- 👁️ Read-only view for unmanaged record types (for example `SOA`)
- 🛡️ Server-side protected zones (`PROTECTED_ZONES`) that cannot be modified or deleted
- ⚡ FastAPI backend acting as a thin adapter over the PowerDNS REST API
- 🔐 Keycloak authentication for write operations; read operations remain public
- 🐳 Self-contained Docker Compose stack with PowerDNS, Keycloak, Caddy and the web application
- 🧪 Backend unit tests with mocked PowerDNS using `respx`

## Architecture

The stack is composed of the following components:

| Component | Description |
|---|---|
| `backend/` | FastAPI application exposing the REST API and acting as a thin adapter over PowerDNS |
| `frontend/` | Vue 3 + Vite single-page application served by nginx |
| `vendors/pdns/seed.sh` | Seeds the demo `example.test.` zone |
| `vendors/keycloak/realm-export.json` | Development Keycloak realm imported at startup |
| `docker-compose.yml` | Local development stack |
| `Caddyfile` | Reverse proxy routing requests to the appropriate service |

Authentication is provided by Keycloak using OIDC, while the backend validates JWTs against the realm's JWKS. See the sections below for authentication and deployment details.

## Identity (Keycloak)

The development stack includes a preconfigured Keycloak instance running in development mode and exposed through Caddy under `/auth`.

Default credentials:

| User | Password |
|---|---|
| `demo` | `demo` |

The Keycloak admin console is intentionally not exposed through the edge proxy. Administrative tasks can still be performed from inside the container using `kcadm.sh`.

### Accessing from another machine

To access the application from another machine on the network, set `PUBLIC_ORIGIN` to the address reachable by other clients:

```bash
PUBLIC_ORIGIN=http://<host-ip>:8080
```

Then recreate the Keycloak container to apply the updated OIDC configuration:

```bash
docker compose up --force-recreate keycloak
```

The default user is intended for development only. Update the credentials before
using the application in a real environment.

### Using an external Keycloak (optional)

The bundled Keycloak instance is intended for development only.
You can use an existing Keycloak installation by overriding the OIDC settings.

Frontend:

```env
OIDC_AUTHORITY=https://keycloak.example.org/realms/<realm>
OIDC_CLIENT_ID=pdns-admin-lite
```

Backend:

```env
OIDC_ISSUER=https://keycloak.example.org/realms/<realm>
OIDC_JWKS_URL=https://keycloak.example.org/realms/<realm>/protocol/openid-connect/certs
OIDC_AUDIENCE=pdns-admin-lite-api
```

Configure a public PKCE client in Keycloak:

- Standard flow enabled
- Client authentication disabled
- PKCE S256 enabled
- Redirect URIs matching the frontend URL
- Audience mapper matching `OIDC_AUDIENCE`

When using an external Keycloak, disable the bundled `keycloak` service.

## Prerequisites

- Docker Engine with Docker Compose v2

For local development:
- Python ≥ 3.13 with [Poetry](https://python-poetry.org/)
- Node.js ≥ 24

## Quick Setup

```bash
cp .env.example .env
docker compose up --build --wait
```

Open <http://localhost:8080>.

The demo `example.test.` zone is already available.

### What to try

After startup:

- Browse zones and records without authentication.
- Log in with the demo user and create or edit a record.
- Try deleting the protected example.test. zone — the operation is rejected.
- Verify that Keycloak admin endpoints are not exposed through the proxy.

## Configuration

The application is configured through environment variables
(see `.env.example`).

Common settings:

| Variable | Purpose |
|---|---|
| `EDGE_PORT` | HTTP port exposed by the reverse proxy |
| `PUBLIC_ORIGIN` | Public URL used by the frontend and authentication flow |
| `PDNS_API_URL` | PowerDNS API endpoint |
| `PDNS_API_KEY` | PowerDNS API key |
| `PROTECTED_ZONES` | Zones that cannot be modified or deleted |

### Advanced configuration

The following variables are mainly used for custom deployments:

| Variable | Purpose |
|---|---|
| `DEFAULT_NS` | Default NS record for newly created zones |
| `KC_ADMIN_USER` / `KC_ADMIN_PASSWORD` | Keycloak bootstrap administrator |
| `PDNS_ADMIN_LITE_USER` / `PDNS_ADMIN_LITE_PASSWORD` | Demo user credentials |
| `OIDC_ISSUER` / `OIDC_JWKS_URL` / `OIDC_AUDIENCE` | Backend token validation settings |

### Connecting to an external PowerDNS server

Set the PowerDNS endpoint and API key in `.env`:

```bash
PDNS_API_URL=http://10.0.0.12:8081/api/v1
PDNS_API_KEY=<real-key>
```

Start the application services without the bundled demo PowerDNS instance:

```bash
docker compose up --build --no-deps edge frontend backend keycloak
```

Before using a real zone:

- Change the default demo credentials
- Configure `PROTECTED_ZONES` with the zones managed by this instance

> The default stack uses HTTP for local development. For a real deployment, configure TLS in Caddy.

## Local development

Backend:

```bash
cd backend
poetry install
poetry run pytest -v
poetry run uvicorn main:app --reload
```

The API is available at `http://localhost:8000` and requires a reachable PowerDNS API endpoint.

Frontend:

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
npm run build   # type-check (vue-tsc) + production bundle
```

The Vite dev server proxies `/api` requests to the backend, so no CORS configuration is required.

Tip: `docker compose up pdns pdns-seed` starts a disposable seeded PowerDNS instance for local development. Add `ports: ["8081:8081"]` to the `pdns` service if you need host access.

See [backend/CONVENTIONS.md](backend/CONVENTIONS.md) and [frontend/CONVENTIONS.md](frontend/CONVENTIONS.md) for backend and frontend development conventions.

## REST API

The backend exposes a small REST API used by the frontend.

| Endpoint | Auth | Description |
|---|---|---|
| `GET /api/health` | Public | Service health check |
| `GET /api/zones` | Public | List available zones |
| `GET /api/zones/{zone_id}` | Public | Get zone details and records |
| `POST /api/zones` | Bearer token | Create a zone |
| `DELETE /api/zones/{zone_id}` | Bearer token | Delete a zone |
| `POST /api/zones/{zone_id}/records` | Bearer token | Create a record |
| `PUT /api/zones/{zone_id}/records` | Bearer token | Replace a record set |
| `DELETE /api/zones/{zone_id}/records` | Bearer token | Delete a record set |

All write operations require a valid Keycloak-issued bearer token. Invalid or missing tokens are rejected by the backend.

Record names can be relative, apex (`@` or empty), or fully qualified.
The backend normalizes names to PowerDNS canonical format before applying protection rules.

![pdns-admin-lite web UI](assets/img/pdns-admin-lite.webp)

## License

This project is licensed under a **No-Commercial License** — see the repository root [LICENSE](LICENSE) file.

## Links

- Main repo — [github.com/Supaahiro/schwifty-lab](https://github.com/Supaahiro/schwifty-lab)
- Blog — [www.schwifty-lab.org](https://www.schwifty-lab.org/)
