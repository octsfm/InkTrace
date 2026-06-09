﻿﻿﻿﻿﻿<template>
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
  border: 1px solid var(--studio-border, var(--ink-border, #d1d5db));
  border-radius: 999px;
  background: var(--studio-card-bg, var(--ink-surface-1, #ffffff));
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--studio-text, var(--ink-text-secondary, #374151));
  cursor: pointer;
  transition: all 0.2s ease;
}

.focus-mode-toggle:hover {
  border-color: var(--ink-accent, #2563eb);
  color: var(--ink-accent, #2563eb);
}

.focus-mode-toggle--active {
  border-color: var(--ink-accent-soft, #bfdbfe);
  background: color-mix(in srgb, var(--ink-accent-soft, #eff6ff) 72%, var(--studio-card-bg, #ffffff));
  color: var(--ink-accent, #2563eb);
}
</style>
