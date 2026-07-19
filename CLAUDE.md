# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal web UI for managing DNS records on a PowerDNS Authoritative server: a FastAPI backend acting as a thin adapter over the PowerDNS REST API, and a Vue 3 + Vite frontend served by nginx, wired together behind a Caddy edge proxy with docker-compose. See [README.md](README.md) for the full feature set, architecture diagram, and how to run the stack.

## Repository Structure

- `backend/` — FastAPI app (Poetry, Python 3.13): `core/pdns.py` PowerDNS client, `core/auth.py` JWT/JWKS verification, `api/routes.py` endpoints, `tests/`. See [backend/CONVENTIONS.md](backend/CONVENTIONS.md).
- `frontend/` — Vue 3 + Vite + TypeScript SPA, multi-stage Dockerfile ending in `nginx:alpine`. See [frontend/CONVENTIONS.md](frontend/CONVENTIONS.md).
- `vendors/pdns/` — Demo PowerDNS seeder (`seed.sh`).
- `vendors/keycloak/` — Checked-in dev-mode Keycloak realm export.
- `.github/` — CI/CD workflows, composite actions, and scripts. See [.github/CLAUDE.md](.github/CLAUDE.md).
- `docker-compose.yml` / `Caddyfile` — dev stack (edge, frontend, backend, demo PowerDNS, Keycloak).

## Build & Development Commands

### Backend (`cd backend`)
```bash
poetry install
poetry run pytest -v                 # unit tests, PowerDNS mocked with respx
poetry run uvicorn main:app --reload # http://localhost:8000, needs a reachable PDNS_API_URL
```

### Frontend (`cd frontend`)
```bash
npm install
npm run dev     # http://localhost:5173, proxies /api to http://localhost:8000
npm run build   # type-check (vue-tsc) + production bundle
```

### Full stack
```bash
cp .env.example .env
docker compose up --build   # http://localhost:8080
```

### Root (repo tooling)
```bash
npm install           # installs commitlint + husky (git hooks)
pip install yamllint   # required for the yamllint pre-commit hook
```

## Commit Convention

Enforced by commitlint via a Husky `commit-msg` hook. Format: `<type>(<scope>): <Subject>`

- **Types:** feat, fix, hotfix, release, refactor, perf, test, docs, chore, ci, build, revert
- **Scope:** optional, lowercase
- **Subject:** sentence-case, max 72 chars, no trailing period
- **Body/footer:** max 100 chars per line

## Git Branching (GitFlow)

Semantic versioning via GitVersion (ContinuousDeployment mode, see `GitVersion.yml`):
- `master` — stable releases (patch increment)
- `develop` — pre-releases (minor increment)
- `feature/*`, `fix/*`, `perf/*`, `refactor/*`, `docs/*`, `style/*`, `test/*`, `ci/*` — from `develop`
- `release/*` — release candidates, from `develop` into `master`
- `hotfix/*` — from `master`
- `chore/*` — from `master`, bypasses the release cycle

## CI/CD

`release.yml` triggers on push to `master`/`hotfix/*`/`develop` (paths: `backend/**`, `frontend/**`). Its `compute` job decides whether to publish, based on branch and (for `develop`) a `[pre-release]` marker in the commit message, then delegates to the reusable `_build-and-release.yml`, which builds and pushes versioned, OCI-labeled images to GHCR (`pdns-admin-lite-backend`, `pdns-admin-lite-frontend`) and cuts a GitHub Release on stable builds. `pr-validate.yml` runs on every PR into `develop`/`master`: backend tests, frontend build, YAML lint, and a push:false Docker build check for whichever Dockerfile changed. Full conventions in [.github/CLAUDE.md](.github/CLAUDE.md).
