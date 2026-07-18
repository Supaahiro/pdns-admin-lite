#!/usr/bin/env bash
# .github/scripts/compute-docker-tags.sh
#
# Purpose:  Compute Docker image tags for a given image and version.
# Usage:    compute-docker-tags.sh <image> <version> <is_prerelease>
# Args:
#   $1  IMAGE          Full image ref without tag (e.g. ghcr.io/owner/my-image)
#   $2  VERSION        SemVer string (e.g. 1.3.0-dev.5)
#   $3  IS_PRERELEASE  "true" or "false"
# Output: Comma-separated tag list to stdout.
# Example:
#   TAGS=$(./compute-docker-tags.sh ghcr.io/owner/app 1.2.0 false)
#   # => ghcr.io/owner/app:1.2.0,ghcr.io/owner/app:latest
# Version: 1.0.0 (2026-07-18)
#
# Changelog:
#   1.0.0 - Baseline: version tag for prereleases, version + latest for
#           releases. Adopted verbatim from blog (generic, no changes needed).

set -euo pipefail

IMAGE="${1:?IMAGE is required}"
VERSION="${2:?VERSION is required}"
IS_PRERELEASE="${3:?IS_PRERELEASE is required (true or false)}"

TAGS="${IMAGE}:${VERSION}"

if [ "${IS_PRERELEASE}" = "false" ]; then
  TAGS="${TAGS},${IMAGE}:latest"
fi

echo "${TAGS}"
