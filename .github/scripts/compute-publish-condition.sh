#!/usr/bin/env bash
# .github/scripts/compute-publish-condition.sh
#
# Purpose:  Decide whether the current run should publish artifacts, based on
#           trigger event + branch.
# Usage:    compute-publish-condition.sh
# Env vars:
#   BRANCH         (required) e.g. "develop", "master", "hotfix/x"
#   EVENT          (required) "push" or "workflow_dispatch"
#   COMMIT_MSG     (optional) head commit message — only read on master pushes,
#                  to detect chore/* merge commits (empty on workflow_dispatch)
#   GITHUB_OUTPUT  (required) provided by GitHub Actions
# Outputs (appended to $GITHUB_OUTPUT):
#   publish, is_prerelease
# Requirements:
#   - git history available (caller must checkout with fetch-depth: 0).
#
#   push to master            → publish stable, unless the merge commit comes
#                               from a chore/* branch (Flow 5 master-bypass —
#                               chore stays outside the release cycle)
#   dispatch on master/main   → REFUSED (exit 1): would re-publish a second
#                               release of an already-released stable version
#   dispatch on hotfix/*      → publish stable — the release is cut from the
#                               branch itself (hotfixes are never merged back)
#   dispatch on any other ref → publish pre-release
#   dispatch, HEAD tagged v*  → REFUSED (exit 1): this commit has already been
#                               published; re-running would duplicate it
#
# Version: 2.0.0 (2026-07-19)
#
# Changelog:
#   2.0.0 - Release-trigger redesign (ported from blog's script 2.0.0): the
#           [pre-release] marker logic is gone. push only fires on master
#           (always stable, with a chore/* merge-commit skip); hotfix and
#           pre-release builds are workflow_dispatch-only, refused on
#           master/main and on an already release-tagged HEAD. New required
#           env var: EVENT. Still no dotnet/ng configuration outputs — this
#           repo always builds production images.
#   1.0.0 - Baseline: branch + [pre-release]-marker publish gate with
#           stable-tag skip on develop, adapted from blog's script (dropped
#           dotnet_configuration/ng_configuration — this repo always builds
#           production images regardless of branch; only the version tag
#           differs between a pre-release and a stable release).

set -euo pipefail

: "${BRANCH:?BRANCH env var is required}"
: "${EVENT:?EVENT env var is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT env var is required}"
COMMIT_MSG="${COMMIT_MSG:-}"

# Defaults: publish disabled until proven otherwise.
publish=false
is_prerelease=false

case "$EVENT" in
  push)
    case "$BRANCH" in
      master | main)
        # Flow 5 master-bypass: a chore/* merge bypasses the release cycle.
        # Merge commits only on master (Inviolable Rule 6), so the subject
        # line is predictable for both PR and manual merges.
        if printf '%s' "$COMMIT_MSG" | grep -qE "^Merge (pull request #[0-9]+ from [^ ]+/chore/|branch 'chore/)"; then
          echo "Merge commit comes from a chore/* branch — skipping release (chore bypasses the release cycle)"
        else
          publish=true
        fi
        ;;
      *)
        echo "Push to '$BRANCH' is not a release trigger — nothing to publish"
        ;;
    esac
    ;;

  workflow_dispatch)
    case "$BRANCH" in
      master | main)
        echo "::error::Refusing workflow_dispatch on '$BRANCH' — it would re-publish a second release of an already-released stable version. Stable releases are cut by merging develop into master."
        exit 1
        ;;
      hotfix/*)
        publish=true
        ;;
      *)
        is_prerelease=true
        publish=true
        ;;
    esac

    existing_tag="$(git tag --points-at HEAD | grep -E '^v[0-9]' || true)"
    if [ -n "$existing_tag" ]; then
      echo "::error::Refusing workflow_dispatch on '$BRANCH' — HEAD already carries release tag(s) '${existing_tag//$'\n'/, }'; publishing again would duplicate an already-released version."
      exit 1
    fi
    ;;

  *)
    echo "::error::Unsupported trigger event '$EVENT'"
    exit 1
    ;;
esac

echo "── Publish condition ──"
echo "Event:           $EVENT"
echo "Branch:          $BRANCH"
echo "Publish:         $publish"
echo "Is pre-release:  $is_prerelease"

{
  echo "publish=$publish"
  echo "is_prerelease=$is_prerelease"
} >> "$GITHUB_OUTPUT"
