<template>
  <button
    type="button"
    class="manual-sync-button"
    :disabled="disabled"
    data-test="manual-sync-button"
    @click="$emit('sync')"
  >
    {{ label }}
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  saving: {
    type: Boolean,
    default: false
  }
})

defineEmits(['sync'])

const label = computed(() => (props.saving ? '同步中...' : '立即同步'))
</script>

<style scoped>
.manual-sync-button {
  border: 1px solid var(--ink-accent-soft, #bfdbfe);
  border-radius: 999px;
  background: color-mix(in srgb, var(--ink-accent-soft, #eff6ff) 72%, var(--studio-card-bg, #ffffff));
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-accent, #1d4ed8);
  cursor: pointer;
}

.manual-sync-button:disabled {
  border-color: var(--studio-border, var(--ink-border, #e5e7eb));
  background: var(--studio-bg-focus, var(--ink-surface-2, #f9fafb));
  color: var(--studio-muted, var(--ink-text-muted, #9ca3af));
  cursor: not-allowed;
}
</style>
