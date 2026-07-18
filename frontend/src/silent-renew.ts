// Loaded only inside the hidden iframe UserManager opens for signinSilent()'s
// no-refresh-token fallback (see auth.ts). It has one job: hand the
// authorization response on this URL back to the parent window's
// UserManager, which is listening for it. Deliberately not the full Vue app.
import { UserManager } from "oidc-client-ts";

import { oidcClientId, resolveOidcAuthority } from "./oidcSettings";

new UserManager({
  authority: resolveOidcAuthority(),
  client_id: oidcClientId,
  // Required by the settings type; unused on this code path.
  redirect_uri: `${window.location.origin}/callback`,
}).signinSilentCallback();
