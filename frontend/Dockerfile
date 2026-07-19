# frontend/Dockerfile
# Version: 1.3.0 (2026-07-19)
#
# Changelog:
#   1.3.0 - Extend the runtime-injection pattern from 1.2.0 to OIDC_AUTHORITY
#           and OIDC_CLIENT_ID: a Keycloak on a different origin than the SPA
#           (e.g. a platform Keycloak instead of the bundled one) needs an
#           absolute authority URL, which VITE_OIDC_AUTHORITY couldn't provide
#           per-environment from a single built image. oidcSettings.ts now
#           reads window.__ENV__.OIDC_AUTHORITY/OIDC_CLIENT_ID, falling back
#           to the same relative-path defaults as before when unset.
#   1.2.0 - Add runtime-overridable ENVIRONMENT (default DEVELOPMENT): unlike
#           BUILD_VERSION below, this is NOT baked at build time — Vite env
#           vars can't be changed post-build, but whoever runs this image
#           needs to be able to flip it to PRODUCTION without a rebuild. So
#           it's a plain container ENV, resolved into env.js at container
#           *start* by docker-entrypoint.d/20-envsubst-runtime-env.sh
#           (envsubst over public/env.template.js) — nginx's official
#           entrypoint runs every executable script under
#           /docker-entrypoint.d/ before starting nginx. App.vue reads
#           window.__ENV__.ENVIRONMENT to show the DEV badge.
#   1.1.0 - Bake BUILD_VERSION/BUILD_SHA/BUILD_DATE: exposed to the Vite build
#           as VITE_APP_* env vars (Vite inlines them into the bundle at build
#           time, no environment-file generation step needed — see
#           src/vite-env.d.ts), displayed in the footer, plus OCI image labels
#           on the runtime stage.
#   1.0.0 - Baseline: two-stage build — Vite production build on
#           node:24-alpine, served by nginx.

FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

COPY . .

ARG BUILD_VERSION=0.0.0-dev.0
ARG BUILD_SHA=unknown
ARG BUILD_DATE=unknown

# Vite inlines any VITE_-prefixed var visible in the build's process.env into
# import.meta.env.* at build time — no separate environment file to generate.
ENV VITE_APP_VERSION=${BUILD_VERSION} \
    VITE_APP_SHA=${BUILD_SHA} \
    VITE_APP_BUILD_DATE=${BUILD_DATE}

RUN npm run build

FROM nginx:1.28-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=build /app/dist /usr/share/nginx/html

COPY docker-entrypoint.d/20-envsubst-runtime-env.sh /docker-entrypoint.d/20-envsubst-runtime-env.sh
RUN chmod +x /docker-entrypoint.d/20-envsubst-runtime-env.sh

ARG BUILD_VERSION=0.0.0-dev.0
ARG BUILD_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.revision="${BUILD_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="pdns-admin-lite-frontend" \
      org.opencontainers.image.source="https://github.com/Supaahiro/pdns-admin-lite"

# Default for local `docker run`/one-off use; docker-compose.yml and anyone
# else running this image can override without a rebuild (see the entrypoint
# script above).
ENV ENVIRONMENT=DEVELOPMENT

EXPOSE 80
