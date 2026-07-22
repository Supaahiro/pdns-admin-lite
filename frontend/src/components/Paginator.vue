<script setup lang="ts">
import { computed } from "vue";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

const props = defineProps<{ total: number; page: number; pageSize: number }>();

const emit = defineEmits<{
  "update:page": [page: number];
  "update:pageSize": [pageSize: number];
}>();

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));

function goTo(page: number): void {
  emit("update:page", Math.min(Math.max(page, 1), pageCount.value));
}

function onPageSizeChange(event: Event): void {
  emit("update:pageSize", Number((event.target as HTMLSelectElement).value));
  emit("update:page", 1);
}
</script>

<template>
  <div v-if="total > pageSize" class="paginator">
    <span class="muted">Page {{ page }} of {{ pageCount }}</span>
    <button type="button" class="secondary" :disabled="page <= 1" @click="goTo(page - 1)">
      Prev
    </button>
    <button type="button" class="secondary" :disabled="page >= pageCount" @click="goTo(page + 1)">
      Next
    </button>
    <label class="page-size">
      Per page
      <select :value="pageSize" @change="onPageSizeChange">
        <option v-for="size in PAGE_SIZE_OPTIONS" :key="size" :value="size">{{ size }}</option>
      </select>
    </label>
  </div>
</template>
