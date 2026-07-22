<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { RECORD_TYPES, type RRSet } from "../api/types";
import { useAuth } from "../auth";
import Paginator from "./Paginator.vue";

const props = defineProps<{ rrsets: RRSet[]; zoneName: string; protected: boolean }>();

const emit = defineEmits<{
  edit: [rrset: RRSet];
  remove: [rrset: RRSet];
}>();

const { isAuthenticated } = useAuth();

const filter = ref("");
const page = ref(1);
const pageSize = ref(10);

const filteredRrsets = computed(() => {
  const needle = filter.value.trim().toLowerCase();
  if (needle === "") {
    return props.rrsets;
  }
  return props.rrsets.filter(
    (rrset) =>
      rrset.name.toLowerCase().includes(needle) ||
      rrset.type.toLowerCase().includes(needle) ||
      rrset.records.some((record) => record.content.toLowerCase().includes(needle)),
  );
});

const pagedRrsets = computed(() =>
  filteredRrsets.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value),
);

// A save/delete reloads the whole rrsets array — the previously-shown page
// may no longer exist, same as a filter change narrowing the result set.
watch([filter, () => props.rrsets], () => {
  page.value = 1;
});

function isManaged(rrset: RRSet): boolean {
  // SOA (and anything else outside the UI's type whitelist) stays read-only.
  return (RECORD_TYPES as readonly string[]).includes(rrset.type);
}

function isProtectedApexNs(rrset: RRSet): boolean {
  // Mirrors the backend's apex-NS guard: rewriting/deleting apex NS is
  // functionally zone destruction, blocked only for the protected zone
  // itself — a subzone's own apex NS is a normal delegation record.
  return props.protected && rrset.type === "NS" && rrset.name === props.zoneName;
}

const copiedContent = ref("");
let copiedTimer: ReturnType<typeof setTimeout> | undefined;

async function copyContent(content: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(content);
  } catch {
    return; // Clipboard permission denied or unavailable — no feedback, no crash.
  }
  copiedContent.value = content;
  clearTimeout(copiedTimer);
  copiedTimer = setTimeout(() => {
    copiedContent.value = "";
  }, 1500);
}
</script>

<template>
  <input
    v-if="rrsets.length > 0"
    v-model="filter"
    id="record-filter"
    class="record-filter"
    placeholder="Filter by name, type, or content…"
  />
  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>TTL</th>
          <th>Content</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rrsets.length > 0 && filteredRrsets.length === 0">
          <td colspan="5" class="muted">No records match "{{ filter }}".</td>
        </tr>
        <tr v-for="rrset in pagedRrsets" :key="`${rrset.name}/${rrset.type}`">
          <td class="mono">{{ rrset.name }}</td>
          <td><span class="tag">{{ rrset.type }}</span></td>
          <td>{{ rrset.ttl }}</td>
          <td class="mono">
            <div v-for="record in rrset.records" :key="record.content" class="record-content">
              <span>{{ record.content }}</span>
              <span v-if="record.disabled" class="muted">(disabled)</span>
              <button
                type="button"
                class="copy-button"
                :title="`Copy ${record.content}`"
                @click="copyContent(record.content)"
              >
                {{ copiedContent === record.content ? "Copied" : "Copy" }}
              </button>
            </div>
          </td>
          <td class="actions">
            <template v-if="isManaged(rrset) && isAuthenticated">
              <template v-if="isProtectedApexNs(rrset)">
                <button disabled title="Protected zone — set PROTECTED_ZONES to change">Edit</button>
                <button class="danger" disabled title="Protected zone — set PROTECTED_ZONES to change">
                  Delete
                </button>
              </template>
              <template v-else>
                <button @click="emit('edit', rrset)">Edit</button>
                <button class="danger" @click="emit('remove', rrset)">Delete</button>
              </template>
            </template>
            <span v-else-if="isManaged(rrset)" class="muted">Sign in to edit</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <Paginator v-model:page="page" v-model:page-size="pageSize" :total="filteredRrsets.length" />
</template>
