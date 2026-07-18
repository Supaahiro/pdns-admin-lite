<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { createZone, formatError, getZones } from "../api/client";
import type { ZoneSummary } from "../api/types";
import { useAuth } from "../auth";

const router = useRouter();
const { isAuthenticated } = useAuth();

const zones = ref<ZoneSummary[]>([]);
const loading = ref(true);
// Page-level, dismissible: distinct from createError below (field-adjacent).
const pageError = ref("");

const showCreate = ref(false);
const newZoneName = ref("");
const creating = ref(false);
const createError = ref("");

// Client-side hint only — the backend's validate_zone_name() is authoritative.
const LDH_ZONE_HINT = /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.?)+$/i;
const nameHint = computed(() => {
  const name = newZoneName.value.trim();
  if (name === "") {
    return "";
  }
  return LDH_ZONE_HINT.test(name)
    ? ""
    : "Use letters, digits, and hyphens only; punycode (xn--...) for internationalized names.";
});

async function load(): Promise<void> {
  loading.value = true;
  pageError.value = "";
  try {
    zones.value = await getZones();
  } catch (err) {
    pageError.value = formatError(err);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function openCreate(): void {
  newZoneName.value = "";
  createError.value = "";
  showCreate.value = true;
}

function cancelCreate(): void {
  showCreate.value = false;
}

async function submitCreate(): Promise<void> {
  if (newZoneName.value.trim() === "") {
    return;
  }
  creating.value = true;
  createError.value = "";
  try {
    const zone = await createZone({ name: newZoneName.value.trim() });
    showCreate.value = false;
    router.push({ name: "zone-detail", params: { zoneId: zone.id } });
  } catch (err) {
    createError.value = formatError(err);
  } finally {
    creating.value = false;
  }
}
</script>

<template>
  <div class="zone-header">
    <h1>Zones</h1>
    <button v-if="!showCreate && isAuthenticated" @click="openCreate">Create zone</button>
  </div>
  <form v-if="showCreate" class="record-form" @submit.prevent="submitCreate">
    <h2>Create zone</h2>
    <label>
      Name
      <input v-model="newZoneName" placeholder="e.g. lab.test or lan" autofocus />
    </label>
    <p v-if="nameHint" class="error">{{ nameHint }}</p>
    <p v-if="createError" class="error">{{ createError }}</p>
    <div class="form-actions">
      <button type="submit" :disabled="newZoneName.trim() === '' || creating">
        {{ creating ? "Creating…" : "Create" }}
      </button>
      <button type="button" class="secondary" @click="cancelCreate">Cancel</button>
    </div>
  </form>
  <p v-if="loading" class="muted">Loading zones…</p>
  <div v-else-if="pageError" class="error banner">
    <span>{{ pageError }}</span>
    <button class="dismiss" aria-label="Dismiss" @click="pageError = ''">×</button>
  </div>
  <p v-else-if="zones.length === 0" class="muted">No zones found.</p>
  <table v-else>
    <thead>
      <tr>
        <th>Name</th>
        <th>Kind</th>
        <th>Serial</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="zone in zones" :key="zone.id">
        <td>
          <RouterLink :to="{ name: 'zone-detail', params: { zoneId: zone.id } }">
            {{ zone.name }}
          </RouterLink>
        </td>
        <td>{{ zone.kind }}</td>
        <td>{{ zone.serial }}</td>
        <td>
          <span v-if="zone.protected" class="tag protected" title="Protected — see PROTECTED_ZONES">
            🛡 protected
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</template>
