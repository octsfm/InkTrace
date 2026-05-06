<template>
  <button
    type="button"
    class="focus-mode-toggle"
    :class="{ 'focus-mode-toggle--active': enabled }"
    :aria-pressed="enabled ? 'true' : 'false'"
    :title="enabled ? '退出专注模式' : '进入专注模式'"
    data-test="focus-mode-toggle"
    @mousedown.prevent
    @click="$emit('toggle')"
  >
    {{ enabled ? '退出专注' : '进入专注' }}
  </button>
</template>

<script setup>
defineProps({
  enabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle'])
</script>

<style scoped>
.focus-mode-toggle {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #ffffff;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s ease;
}

.focus-mode-toggle:hover {
  border-color: #93c5fd;
  color: #1d4ed8;
}

.focus-mode-toggle--active {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}
</style>
