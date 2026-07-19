#!/bin/sh
# frontend/docker-entrypoint.d/20-envsubst-runtime-env.sh
#
# Purpose: Generate env.js from env.template.js at container *start* time,
#          substituting the container's actual ENVIRONMENT/OIDC_AUTHORITY/
#          OIDC_CLIENT_ID values — not ones baked in at image build time.
#          This is what lets whoever runs the image override them with
#          `docker run -e ENVIRONMENT=PRODUCTION` or a compose
#          `environment:` entry, with no rebuild required. OIDC_AUTHORITY in
#          particular has to be settable this way: a Keycloak on a different
#          origin than the SPA needs an absolute authority URL, and images
#          are built once and reused across environments (see oidcSettings.ts).
# Runs via nginx's official entrypoint, which executes every executable
# *.sh script under /docker-entrypoint.d/ before starting nginx.
set -eu

envsubst '${ENVIRONMENT} ${OIDC_AUTHORITY} ${OIDC_CLIENT_ID}' \
  < /usr/share/nginx/html/env.template.js \
  > /usr/share/nginx/html/env.js
