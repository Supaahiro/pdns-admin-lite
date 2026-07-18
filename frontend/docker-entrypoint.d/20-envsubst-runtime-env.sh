#!/bin/sh
# frontend/docker-entrypoint.d/20-envsubst-runtime-env.sh
#
# Purpose: Generate env.js from env.template.js at container *start* time,
#          substituting the container's actual ENVIRONMENT value — not the
#          one baked in at image build time. This is what lets whoever runs
#          the image override it with `docker run -e ENVIRONMENT=PRODUCTION`
#          or a compose `environment:` entry, with no rebuild required.
# Runs via nginx's official entrypoint, which executes every executable
# *.sh script under /docker-entrypoint.d/ before starting nginx.
set -eu

envsubst '${ENVIRONMENT}' \
  < /usr/share/nginx/html/env.template.js \
  > /usr/share/nginx/html/env.js
