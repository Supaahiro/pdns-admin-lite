import { InMemoryWebStorage, User, UserManager, WebStorageStateStore } from "oidc-client-ts";
import { computed, ref } from "vue";

import { oidcClientId, resolveOidcAuthority } from "./oidcSettings";

// In-memory only, never localStorage: XSS must not yield durable tokens. The
// cost — losing tokens on hard refresh — is recovered by initAuth()'s
// signinSilent() attempt: with no refresh token in memory yet after a
// refresh, that falls back to an iframe hitting silent_redirect_uri, which
// succeeds silently if Keycloak's SSO session cookie is still valid.
const userManager = new UserManager({
  authority: resolveOidcAuthority(),
  client_id: oidcClientId,
  redirect_uri: `${window.location.origin}/callback`,
  silent_redirect_uri: `${window.location.origin}/silent-renew.html`,
  post_logout_redirect_uri: window.location.origin,
  response_type: "code",
  scope: "openid profile email",
  userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
  automaticSilentRenew: true,
});

const currentUser = ref<User | null>(null);

userManager.events.addUserLoaded((user) => {
  currentUser.value = user;
});
userManager.events.addUserUnloaded(() => {
  currentUser.value = null;
});
userManager.events.addSilentRenewError((err) => {
  // isAuthenticated is a computed over currentUser.value.expired, which is
  // only re-evaluated when currentUser itself is reassigned — without this,
  // a background renewal failure would leave the UI reporting "logged in"
  // indefinitely even once the access token has actually expired.
  console.error("Silent token renewal failed", err);
  currentUser.value = null;
});

const isAuthenticated = computed(
  () => currentUser.value !== null && currentUser.value.expired !== true,
);

export function useAuth() {
  return {
    user: currentUser,
    isAuthenticated,
    login: (returnTo?: string) => userManager.signinRedirect({ state: { returnTo } }),
    logout: () => userManager.signoutRedirect(),
  };
}

/** Attempts to restore a session from Keycloak's SSO cookie; swallows failure — anonymous is a supported state. */
export async function initAuth(): Promise<void> {
  const existing = await userManager.getUser();
  if (existing && !existing.expired) {
    currentUser.value = existing;
    return;
  }
  try {
    currentUser.value = await userManager.signinSilent();
  } catch {
    currentUser.value = null;
  }
}

/** Completes the OIDC redirect; returns the path the guard sent the user here from. */
export async function completeLogin(): Promise<string> {
  const user = await userManager.signinRedirectCallback();
  currentUser.value = user;
  const state = user.state as { returnTo?: string } | undefined;
  return state?.returnTo || "/";
}

export async function getAccessToken(): Promise<string | null> {
  const user = currentUser.value ?? (await userManager.getUser());
  return user && !user.expired ? user.access_token : null;
}

/** One-shot silent renew for client.ts's single-retry-on-401 policy. */
export async function renewAccessToken(): Promise<string | null> {
  try {
    currentUser.value = await userManager.signinSilent();
    return currentUser.value?.access_token ?? null;
  } catch {
    // A stale currentUser here would leave isAuthenticated (and the router
    // guard) reporting "logged in" even though every request will 401 —
    // clearing it sends the next navigation back through /login for real.
    currentUser.value = null;
    return null;
  }
}
