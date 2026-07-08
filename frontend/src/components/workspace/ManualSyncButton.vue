<template>
  <button
    type="button"
    class="ink-button ink-button--soft manual-sync-button"
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
  min-width: 96px;
}

.manual-sync-button:disabled {
  transform: none;
}
</style>
