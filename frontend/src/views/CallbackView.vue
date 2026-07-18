<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { completeLogin } from "../auth";

const router = useRouter();
const error = ref("");

onMounted(async () => {
  try {
    const returnTo = await completeLogin();
    router.replace(returnTo);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});
</script>

<template>
  <p v-if="error" class="error">Sign-in failed: {{ error }}</p>
  <p v-else class="muted">Completing sign-in…</p>
</template>
