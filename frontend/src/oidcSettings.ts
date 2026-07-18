// Relative by default: Keycloak shares the SPA's origin (routed behind Caddy
// at /auth), so redirects, discovery, and the issuer in tokens all agree
// without any CORS configuration. Shared between auth.ts (the main app) and
// silent-renew.ts (the hidden-iframe callback page), which must agree on
// authority/client_id to belong to the same silent-renew handshake.
export const oidcAuthority: string =
  import.meta.env.VITE_OIDC_AUTHORITY ?? "/auth/realms/pdns-admin-lite";
export const oidcClientId: string = import.meta.env.VITE_OIDC_CLIENT_ID ?? "pdns-admin-lite-spa";

export function resolveOidcAuthority(): string {
  return new URL(oidcAuthority, window.location.origin).toString();
}
