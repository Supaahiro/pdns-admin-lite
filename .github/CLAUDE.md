# CI/CD Reference

## Conventions

Adopted from the `blog` repo's CI structure:

- `_<name>.yml` — reusable workflow (called via `workflow_call`, never triggered directly)
- `<name>.yml` — entry-point workflow (triggered by push/PR, calls reusable workflows or jobs)
- `.github/actions/<name>/` — composite action (callable via `uses: ./.github/actions/<name>`)
- `.github/scripts/<name>.sh` — shell utility (called from workflow `run:` steps)

### Version tracking

Every workflow, composite action, and script carries a header comment with
`Version: X.Y.Z (date)` plus a `Changelog:` list (same convention as `blog`):
patch for corrections, minor for new behavior, major for restructures — bump
it and add a changelog entry with every functional change (comment-only edits
don't bump).

## When NOT to Extract a Composite Action

Do not create a composite action when:
- The logic is fewer than 3 steps with no variation between call sites
- Only one job in this repo uses it and there is no concrete plan for a second
- The "action" is just configuration (login + setup) with no logic

(This is why there's no `setup-node-cached` action here yet — the frontend
job in `pr-validate.yml` is its only call site. Extract it once a second call
site shows up, e.g. an e2e job.)

## Action Version Pins

All `uses:` references must match this table (pins adopted from `blog`, 2026-07-18).

| Action | Pinned version |
|--------|---------------|
| `actions/checkout` | `@v7` |
| `actions/setup-node` | `@v7` |
| `actions/setup-python` | `@v6` |
| `dorny/paths-filter` | `@v4` |
| `docker/login-action` | `@v4` |
| `docker/setup-buildx-action` | `@v4` |
| `docker/build-push-action` | `@v7` |
| `softprops/action-gh-release` | `@v3` |
| `gittools/actions/gitversion/setup` | `@v4` |
| `gittools/actions/gitversion/execute` | `@v4` |

## Composite Actions

### `.github/actions/toolchain/`

Resolves toolchain versions from `.github/versions.json` and exposes each as
an output. **Prerequisite:** caller must `actions/checkout` first.

**Inputs:** `branch` (optional) — override key to apply; defaults to the PR
target branch (`GITHUB_BASE_REF`), else the pushed branch (`GITHUB_REF_NAME`).

**Outputs:** `node`, `python` — trimmed from blog's node/python/dotnet/zensical
superset to the two tools this repo actually uses.

Use it as the first step after checkout, then reference
`${{ steps.toolchain.outputs.<tool> }}` in `setup-*` steps. This is the
single source of truth for tool versions — never hardcode
`node-version`/`python-version` in a workflow.

**Per-branch override:** add the target version under `branchOverrides.<branch>`
in `versions.json` to trial a tool on one branch (e.g. `develop`) before
promoting it to the shared `toolchain` block.

### `.github/actions/gitversion/`

Runs GitVersion, computes short SHA and lowercase owner. No inputs.

**Prerequisite:** caller must check out with `fetch-depth: 0` before invoking.

**Outputs:** `semver`, `sha_short`, `owner`

Trimmed from blog's gitversion action, which also outputs `assembly_semver`/
`assembly_sem_file_ver` for .NET's AssemblyVersion/FileVersion — meaningless
here, since neither the Python backend nor the Vue frontend has an assembly
to version. This repo bakes the version directly: `BUILD_VERSION`/
`BUILD_SHA`/`BUILD_DATE` build-args become OCI image labels on both images,
plus `APP_VERSION` (backend, surfaced in `GET /api/health`) and
`VITE_APP_VERSION` (frontend, inlined into the bundle by Vite, shown in the
footer) — see `backend/Dockerfile` and `frontend/Dockerfile`.

Used by the `compute` job in `release.yml`.

## Config

### `.github/versions.json` *(repo-local)*

Single source of truth for toolchain versions, consumed by
`.github/actions/toolchain`. `toolchain` holds defaults;
`branchOverrides.<branch>` shallow-merges over them for a given branch.

## Scripts

### `.github/scripts/compute-docker-tags.sh`

Args: `<image> <version> <is_prerelease>`. Outputs comma-separated Docker tag list to stdout.

Produces `image:version` for prereleases, `image:version,image:latest` for releases.

### `.github/scripts/compute-publish-condition.sh`

Env: `BRANCH` (required), `COMMIT_MSG` (optional), `GITHUB_OUTPUT` (required). Requires `fetch-depth: 0`.

Decides `publish` / `is_prerelease` from branch + merge-commit message,
appending them to `$GITHUB_OUTPUT`. `master`/`hotfix/*` publish stable;
`develop` publishes a pre-release only when the commit contains
`[pre-release]` and HEAD is not already stable-tagged. Used by `release.yml`.
Trimmed from blog's version of this script, which also emitted
`dotnet_configuration`/`ng_configuration` — not needed here, since this repo
always builds production images regardless of branch; only the version tag
differs between a pre-release and a stable release.

## Workflows

### `pr-validate.yml`

Single PR-validation entry point, triggered on every PR into `develop`/`master`
(no top-level paths filter, so every job always reports a conclusion and
required checks never hang on 'Expected'). `dorny/paths-filter` gates the
`backend`/`frontend` jobs per changed path; `changes-and-lint` runs YAML lint
unconditionally cheap and reports filter outputs for the other jobs to consume.

Imported from schwifty-lab's `pr-validate-pdns-admin-lite.yml` (backend
`poetry install && pytest`, frontend `npm ci && npm run build`), with paths
collapsed from `projects/pdns-admin-lite/{backend,frontend}` to `backend/`
and `frontend/` now that this project is its own repo, and restructured onto
the blog paths-filter/toolchain pattern.

The `docker` job builds (never pushes) whichever image's Dockerfile changed,
reusing the release build's `type=gha` cache read-only (`cache-from` only) —
catches a broken Dockerfile before release time, when a push that doesn't
publish would otherwise build nothing.

### `release.yml` + `_build-and-release.yml`

Push-triggered entry point (`master` / `hotfix/*` / `develop`, path-filtered
on `backend/**` and `frontend/**`) — same split as blog: a `compute` job
gates publishing via `compute-publish-condition.sh` and runs the
`gitversion` composite action (only when publishing), then delegates to the
reusable `_build-and-release.yml`, which builds and pushes both images to
GHCR (`ghcr.io/<owner>/pdns-admin-lite-backend`,
`ghcr.io/<owner>/pdns-admin-lite-frontend`) and creates a GitHub Release
(source archive + checksums only — the images themselves are the deployable
artifact).

Two deliberate simplifications versus blog's version:
- **No CLI image / no shared-layer caching.** Blog's docker jobs use a
  `type=registry` GHCR `:buildcache` tag because its backend and CLI images
  share Dockerfile stages and benefit from sharing that cache. Neither image
  here has a sibling target, so both docker jobs just use `type=gha` —
  simpler, and it means there's no orphaned-buildcache-manifest problem, so
  **no `prune-ghcr-untagged.sh` script or job exists in this repo** (nothing
  ever gets left behind in the registry to prune).
- **No e2e job.** Blog's `e2e` job boots the release's `docker-compose.yml`
  stack and runs a Playwright smoke suite against the just-pushed images
  before the `release` job runs. This repo has no such suite yet — the
  `release` job here only `needs` the two docker jobs. `docker-compose.yml`
  already describes the full stack (edge/frontend/backend/pdns/keycloak), so
  wiring up an e2e job later is mostly "write the smoke tests," not
  "invent the stack."
