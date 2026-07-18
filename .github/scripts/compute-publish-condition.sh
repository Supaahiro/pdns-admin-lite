#!/usr/bin/env bash
# .github/scripts/compute-publish-condition.sh
#
# Purpose:  Decide whether the current push should publish artifacts, based on
#           branch + the merge-commit message.
# Usage:    compute-publish-condition.sh
# Env vars:
#   BRANCH         (required) e.g. "develop", "master", "hotfix/x"
#   COMMIT_MSG     (optional) head commit message
#   GITHUB_OUTPUT  (required) provided by GitHub Actions
# Outputs (appended to $GITHUB_OUTPUT):
#   publish, is_prerelease
# Requirements:
#   - git history available (caller must checkout with fetch-depth: 0).
#
#   master        → publish (stable release)
#   hotfix/*      → publish (stable release)
#   develop       → publish only if the merge commit contains "[pre-release]"
#                   and HEAD does not already carry a stable release tag
#
# Version: 1.0.0 (2026-07-18)
#
# Changelog:
#   1.0.0 - Baseline: branch + [pre-release]-marker publish gate with
#           stable-tag skip on develop, adapted from blog's script (dropped
#           dotnet_configuration/ng_configuration — this repo always builds
#           production images regardless of branch; only the version tag
#           differs between a pre-release and a stable release).

set -euo pipefail

: "${BRANCH:?BRANCH env var is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT env var is required}"
COMMIT_MSG="${COMMIT_MSG:-}"

# Defaults: publish disabled until proven otherwise.
publish=false
is_prerelease=false

case "$BRANCH" in
  master | hotfix/*)
    publish=true
    ;;
  develop)
    is_prerelease=true

    if git tag --points-at HEAD | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
      echo "HEAD already carries a stable release tag — skipping dev pre-release build"
      publish=false
    elif printf '%s' "$COMMIT_MSG" | grep -qF '[pre-release]'; then
      publish=true
    else
      echo "Merge commit does not contain [pre-release] — skipping dev pre-release build"
      publish=false
    fi
    ;;
esac

echo "── Publish condition ──"
echo "Branch:          $BRANCH"
echo "Commit message:  $COMMIT_MSG"
echo "Publish:         $publish"
echo "Is pre-release:  $is_prerelease"

{
  echo "publish=$publish"
  echo "is_prerelease=$is_prerelease"
} >> "$GITHUB_OUTPUT"
