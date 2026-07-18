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

## Config

### `.github/versions.json` *(repo-local)*

Single source of truth for toolchain versions, consumed by
`.github/actions/toolchain`. `toolchain` holds defaults;
`branchOverrides.<branch>` shallow-merges over them for a given branch.

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

## Not Yet Present

No release/publish pipeline exists yet — this repo has no Docker images
published to a registry and no GitHub Releases workflow. `GitVersion.yml` is
already in place (copied from `blog`, same GitFlow) for when one is added;
follow blog's `release.yml` + `_build-and-release.yml` split (push-triggered
compute job → reusable build-and-release workflow) rather than reinventing
the shape.
