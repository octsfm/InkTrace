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
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #eff6ff;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #1d4ed8;
  cursor: pointer;
}

.manual-sync-button:disabled {
  border-color: #e5e7eb;
  background: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
}
</style>
