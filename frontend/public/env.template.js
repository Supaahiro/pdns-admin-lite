// See docker-entrypoint.d/20-envsubst-runtime-env.sh — substituted into env.js at container start.
window.__ENV__ = {
  ENVIRONMENT: "${ENVIRONMENT}",
  OIDC_AUTHORITY: "${OIDC_AUTHORITY}",
  OIDC_CLIENT_ID: "${OIDC_CLIENT_ID}",
};
