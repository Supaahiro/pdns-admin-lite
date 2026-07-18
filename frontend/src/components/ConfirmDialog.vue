<script setup lang="ts">
import { ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    mode?: "confirm" | "type-name";
    confirmName?: string;
    confirmLabel?: string;
    busy?: boolean;
    danger?: boolean;
    error?: string;
  }>(),
  { mode: "confirm", confirmLabel: "Confirm", busy: false, danger: false, error: "" },
);

const emit = defineEmits<{ confirm: []; cancel: [] }>();

const typedName = ref("");

// Reset the typed-name friction each time the dialog opens.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      typedName.value = "";
    }
  },
);

function submit(): void {
  if (props.busy || (props.mode === "type-name" && typedName.value !== props.confirmName)) {
    return;
  }
  emit("confirm");
}
</script>

<template>
  <div v-if="open" class="dialog-backdrop" @click.self="emit('cancel')">
    <div class="dialog" role="dialog" aria-modal="true" :aria-label="title">
      <h2>{{ title }}</h2>
      <div class="dialog-body">
        <slot />
      </div>
      <template v-if="mode === 'type-name'">
        <p class="muted">
          Type <strong class="mono">{{ confirmName }}</strong> to confirm. This cannot be undone.
        </p>
        <input v-model="typedName" :placeholder="confirmName" class="mono" @keyup.enter="submit" />
      </template>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="form-actions">
        <button
          :class="{ danger }"
          :disabled="busy || (mode === 'type-name' && typedName !== confirmName)"
          @click="submit"
        >
          {{ busy ? "Working…" : confirmLabel }}
        </button>
        <button type="button" class="secondary" @click="emit('cancel')">Cancel</button>
      </div>
    </div>
  </div>
</template>
