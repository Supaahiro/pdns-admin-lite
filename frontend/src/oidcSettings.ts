// Relative by default: Keycloak shares the SPA's origin (routed behind Caddy
// at /auth), so redirects, discovery, and the issuer in tokens all agree
// without any CORS configuration. Shared between auth.ts (the main app) and
// silent-renew.ts (the hidden-iframe callback page), which must agree on
// authority/client_id to belong to the same silent-renew handshake.
//
// Read from window.__ENV__ (populated at container *start* time, not build
// time — see public/env.template.js + docker-entrypoint.d/) rather than
// import.meta.env.VITE_OIDC_AUTHORITY: a Keycloak on a different origin than
// the SPA needs an absolute authority URL, and Vite inlines VITE_* vars into
// the bundle once at image build time, before the deployment target (and
// its Keycloak origin) is known. The relative default stays as a fallback so
// nothing breaks for anyone not overriding it.
export const oidcAuthority: string =
  window.__ENV__?.OIDC_AUTHORITY || "/auth/realms/pdns-admin-lite";
export const oidcClientId: string = window.__ENV__?.OIDC_CLIENT_ID || "pdns-admin-lite-spa";

export function resolveOidcAuthority(): string {
  return new URL(oidcAuthority, window.location.origin).toString();
}
