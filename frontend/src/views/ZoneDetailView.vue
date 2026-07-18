<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  createRecord,
  deleteRecord,
  deleteZone,
  formatError,
  getZone,
  updateRecord,
} from "../api/client";
import type { RecordInput, RRSet, ZoneDetail } from "../api/types";
import { useAuth } from "../auth";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import RecordForm from "../components/RecordForm.vue";
import RecordTable from "../components/RecordTable.vue";

const props = defineProps<{ zoneId: string }>();
const router = useRouter();
const { isAuthenticated } = useAuth();

const zone = ref<ZoneDetail | null>(null);
const loading = ref(true);
// Page-level, dismissible: the zone failed to load at all (network/PowerDNS/auth
// misconfiguration) — distinct from the field-adjacent errors below.
const pageError = ref("");
const showForm = ref(false);
const editing = ref<RRSet | null>(null);
const saving = ref(false);
// Shown right above RecordForm: validation/conflict errors from a save.
const formError = ref("");

const recordToDelete = ref<RRSet | null>(null);
const deletingRecord = ref(false);
const recordDeleteError = ref("");

const showDeleteZone = ref(false);
const deletingZone = ref(false);
const zoneDeleteError = ref("");

const serialHighlight = ref(false);
let previousSerial: number | null = null;

async function load(): Promise<void> {
  loading.value = true;
  pageError.value = "";
  try {
    const fresh = await getZone(props.zoneId);
    if (previousSerial !== null && fresh.serial !== previousSerial) {
      serialHighlight.value = true;
      setTimeout(() => {
        serialHighlight.value = false;
      }, 1500);
    }
    previousSerial = fresh.serial;
    zone.value = fresh;
  } catch (err) {
    pageError.value = formatError(err);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function openAdd(): void {
  editing.value = null;
  formError.value = "";
  showForm.value = true;
}

function openEdit(rrset: RRSet): void {
  editing.value = rrset;
  formError.value = "";
  showForm.value = true;
}

function closeForm(): void {
  showForm.value = false;
  editing.value = null;
}

async function save(input: RecordInput): Promise<void> {
  saving.value = true;
  formError.value = "";
  try {
    if (editing.value) {
      await updateRecord(props.zoneId, input);
    } else {
      await createRecord(props.zoneId, input);
    }
    closeForm();
    await load();
  } catch (err) {
    formError.value = formatError(err);
  } finally {
    saving.value = false;
  }
}

function requestRemove(rrset: RRSet): void {
  recordDeleteError.value = "";
  recordToDelete.value = rrset;
}

async function confirmRemoveRecord(): Promise<void> {
  if (!recordToDelete.value) {
    return;
  }
  deletingRecord.value = true;
  recordDeleteError.value = "";
  try {
    await deleteRecord(props.zoneId, recordToDelete.value.name, recordToDelete.value.type);
    recordToDelete.value = null;
    await load();
  } catch (err) {
    recordDeleteError.value = formatError(err);
  } finally {
    deletingRecord.value = false;
  }
}

async function confirmDeleteZone(): Promise<void> {
  deletingZone.value = true;
  zoneDeleteError.value = "";
  try {
    await deleteZone(props.zoneId);
    router.push({ name: "zones" });
  } catch (err) {
    zoneDeleteError.value = formatError(err);
    deletingZone.value = false;
  }
}
</script>

<template>
  <p><RouterLink to="/">← All zones</RouterLink></p>
  <p v-if="loading" class="muted">Loading zone…</p>
  <div v-else-if="pageError && !zone" class="error banner">
    <span>{{ pageError }}</span>
    <button class="dismiss" aria-label="Dismiss" @click="pageError = ''">×</button>
  </div>
  <template v-else-if="zone">
    <div class="zone-header">
      <h1>{{ zone.name }}</h1>
      <span v-if="zone.protected" class="tag protected" title="Protected — see PROTECTED_ZONES">
        🛡 protected
      </span>
      <span class="muted" :class="{ 'serial-highlight': serialHighlight }">
        {{ zone.kind }} · serial {{ zone.serial }}
      </span>
      <button v-if="!showForm && isAuthenticated" @click="openAdd">Add record</button>
      <span v-else-if="!showForm" class="muted auth-hint">Sign in to add records</span>
    </div>
    <div v-if="pageError" class="error banner">
      <span>{{ pageError }}</span>
      <button class="dismiss" aria-label="Dismiss" @click="pageError = ''">×</button>
    </div>
    <p v-if="formError" class="error">{{ formError }}</p>
    <RecordForm
      v-if="showForm"
      :zone-name="zone.name"
      :initial="editing"
      :busy="saving"
      @save="save"
      @cancel="closeForm"
    />
    <RecordTable
      :rrsets="zone.rrsets"
      :zone-name="zone.name"
      :protected="zone.protected"
      @edit="openEdit"
      @remove="requestRemove"
    />

    <div v-if="isAuthenticated" class="danger-zone">
      <button
        class="danger"
        :disabled="zone.protected"
        :title="zone.protected ? 'Protected zone — set PROTECTED_ZONES to change' : ''"
        @click="showDeleteZone = true"
      >
        Delete zone
      </button>
    </div>

    <ConfirmDialog
      :open="recordToDelete !== null"
      title="Delete record set"
      confirm-label="Delete"
      danger
      :busy="deletingRecord"
      :error="recordDeleteError"
      @confirm="confirmRemoveRecord"
      @cancel="recordToDelete = null"
    >
      <p v-if="recordToDelete">
        Delete the <strong>{{ recordToDelete.type }}</strong> record set
        <strong class="mono">{{ recordToDelete.name }}</strong>?
      </p>
      <ul v-if="recordToDelete" class="mono">
        <li v-for="record in recordToDelete.records" :key="record.content">
          {{ record.content }}
        </li>
      </ul>
    </ConfirmDialog>

    <ConfirmDialog
      :open="showDeleteZone"
      title="Delete zone"
      mode="type-name"
      :confirm-name="zone.name"
      confirm-label="Delete zone"
      danger
      :busy="deletingZone"
      :error="zoneDeleteError"
      @confirm="confirmDeleteZone"
      @cancel="showDeleteZone = false"
    >
      <p>
        This permanently deletes <strong class="mono">{{ zone.name }}</strong> and every record in
        it from PowerDNS.
      </p>
    </ConfirmDialog>
  </template>
</template>
