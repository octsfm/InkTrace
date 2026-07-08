<template>
  <button
    type="button"
    class="ink-button focus-mode-toggle"
    :class="enabled ? 'ink-button--soft focus-mode-toggle--active' : 'ink-button--ghost'"
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
  min-width: 96px;
}

.focus-mode-toggle:hover {
  color: var(--ink-accent, #2563eb);
}

.focus-mode-toggle--active {
  color: var(--ink-accent, #2563eb);
}
</style>
