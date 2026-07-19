// Fallback for `npm run dev` / `vite preview`, where there's no nginx
// entrypoint to run envsubst. In the built container this file is
// overwritten at every start by docker-entrypoint.d/20-envsubst-runtime-env.sh
// with the container's actual ENVIRONMENT/OIDC_* — see env.template.js.
// OIDC_* are left empty so oidcSettings.ts falls back to its own defaults.
window.__ENV__ = {
  ENVIRONMENT: "DEVELOPMENT",
  OIDC_AUTHORITY: "",
  OIDC_CLIENT_ID: "",
};
