<script setup lang="ts">
import { useRoute } from "vue-router";

import { useAuth } from "../auth";

const route = useRoute();
const { login } = useAuth();

function signIn(): void {
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : undefined;
  login(redirect);
}
</script>

<template>
  <div class="login-gate">
    <div class="login-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="5" y="11" width="14" height="9" rx="1.5" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </svg>
    </div>
    <h1>Sign in to manage your DNS records</h1>
    <p class="muted">You need to log in to view and edit the PowerDNS zones tied to your account.</p>
    <button @click="signIn">Login now</button>
  </div>
</template>
