# CLAUDE.md

## Working with the project owner

Implementation and architectural decisions belong to the user. When the user
makes a choice, follow it: do not challenge it, reopen the discussion, or replace
it with a solution you prefer. If a concrete technical obstacle arises, describe
it with supporting evidence and ask only for the clarification needed to proceed.
A different preference is not an obstacle.

Do not independently introduce new rules, prohibitions, or permanent constraints
for the project. Your choices during a task do not become the user's decisions.
This file describes the project and helps readers navigate the code; it is not a
record of prescriptions accumulated from previous sessions.

Do not modify this document without the user's explicit consent.

## What pdns-admin-lite is

A web interface for managing DNS records on a PowerDNS Authoritative server.
The backend is a Python 3.12+ FastAPI adapter over the PowerDNS REST API, with
JWT/JWKS authentication. The frontend uses Vue 3, TypeScript, and Vite.

Docker Compose runs the backend, the frontend served by nginx, a Caddy edge proxy,
and development instances of PowerDNS and Keycloak.

## Where the code lives

| Path | Contents |
|---|---|
| `backend/` | FastAPI application, uv dependencies, and tests |
| `backend/core/pdns.py`, `backend/core/auth.py` | PowerDNS client and JWT/JWKS verification |
| `backend/api/routes.py` | HTTP endpoints |
| `frontend/` | Vue application, Vite configuration, and frontend Dockerfile |
| `vendors/pdns/`, `vendors/keycloak/` | Demo DNS seeder and development Keycloak realm |
| `docker-compose.yml`, `Caddyfile` | Local stack and edge routing |
| `.github/` | PR validation, release workflows, actions, and scripts |

## Build and tests

Run checks for the component affected by a change. Backend tests use pytest and
mock PowerDNS with respx; running the application itself requires a reachable
`PDNS_API_URL`. The frontend build runs TypeScript checks through `vue-tsc`
before producing the Vite bundle; there is no frontend test script.

PR validation runs backend tests, the frontend build, YAML lint, and Docker build
checks according to changed paths. The workflow is
`.github/workflows/pr-validate.yml`; CI details are in `.github/CLAUDE.md`.
Repeat checks after relevant changes or to investigate a failure.

## Essential commands

From `backend/`:

```bash
uv sync --locked
uv run --locked pytest -v
uv run --locked uvicorn main:app --reload
```

For an existing Conda environment, see the `UV_PROJECT_ENVIRONMENT` and
`--inexact` instructions in `README.md`.

From `frontend/`:

```bash
npm install
npm run dev
npm run build
```

From the repository root, to configure and start the local stack:

```bash
cp .env.example .env
docker compose up --build
```

The stack is served at `http://localhost:8080`. The standalone frontend dev server
uses port 5173 and proxies API requests to the backend on port 8000.

For repository tooling, from the root:

```bash
npm install
pip install yamllint
yamllint -c .yamllint.yml .
```

Commits follow `<type>(<scope>): <Subject>`, enforced by commitlint and Husky.
The optional scope is lowercase; the subject is sentence-case, at most 72
characters, without a trailing period. Body and footer lines are at most 250
characters. See `.commitlintrc.yml` for the accepted types.

The repository uses Gitflow and GitVersion; `GitVersion.yml` defines branch
sources and version increments. Stable releases come from `master`;
`chore/*` branches from `master` bypass publishing. Manual releases from
`hotfix/*` are stable, while other eligible branches produce prereleases.
`.github/workflows/release.yml` delegates image publishing to
`.github/workflows/_build-and-release.yml`.

The overview and stack setup are in `README.md`. Code conventions are in
`backend/CONVENTIONS.md` and `frontend/CONVENTIONS.md`; workflow guidance is
in `.github/CLAUDE.md`.
