// See docker-entrypoint.d/20-envsubst-runtime-env.sh — substituted into env.js at container start.
window.__ENV__ = {
  ENVIRONMENT: "${ENVIRONMENT}",
};
