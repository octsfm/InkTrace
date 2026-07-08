<template>
  <div
    v-if="visible"
    class="selection-rewrite-toolbar"
    :class="`selection-rewrite-toolbar--${placement}`"
    :style="floatingStyle"
    data-test="selection-rewrite-toolbar"
    :aria-busy="busy ? 'true' : 'false'"
  >
    <div
      v-if="polling"
      class="selection-rewrite-toolbar__status"
      data-test="selection-rewrite-toolbar-status"
    >
      <span>{{ POLLING_TEXT }}</span>
      <span class="selection-rewrite-toolbar__status-bar" />
    </div>
    <button
      v-for="item in modeOptions"
      :key="item.id"
      type="button"
      class="selection-rewrite-toolbar__button"
      :data-test="`selection-rewrite-mode-${item.id}`"
      :disabled="busy"
      @click="$emit('mode-select', item.id)"
    >
      {{ item.label }}
    </button>
    <button
      type="button"
      class="selection-rewrite-toolbar__button selection-rewrite-toolbar__button--secondary"
      data-test="selection-rewrite-clear-history"
      :disabled="busy"
      @click="$emit('clear-history')"
    >
      {{ CLEAR_HISTORY_TEXT }}
    </button>
  </div>
</template>

<script setup>
const POLLING_TEXT = '正在生成，请稍等'
const CLEAR_HISTORY_TEXT = '清除历史改写'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  busy: {
    type: Boolean,
    default: false
  },
  polling: {
    type: Boolean,
    default: false
  },
  floatingStyle: {
    type: Object,
    default: () => ({})
  },
  placement: {
    type: String,
    default: 'above'
  }
})

defineEmits(['mode-select', 'clear-history'])

const modeOptions = [
  { id: 'expand', label: '扩写' },
  { id: 'rewrite', label: '重写' },
  { id: 'abbreviate', label: '缩写' },
  { id: 'polish', label: '润色' },
  { id: 'dialogue_opt', label: '对白优化' },
  { id: 'de_ai', label: '降低 AI 味' }
]
</script>

<style scoped>
.selection-rewrite-toolbar {
  position: absolute;
  z-index: 18;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 320px;
  padding: 12px;
  border: 1px solid var(--studio-border, var(--ink-border));
  border-radius: 20px;
  background: var(--studio-card-bg, var(--ink-surface-1));
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
}

.selection-rewrite-toolbar--above {
  transform: translate(-50%, calc(-100% - 12px));
}

.selection-rewrite-toolbar--below {
  transform: translate(-50%, 12px);
}

.selection-rewrite-toolbar__status {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  font-size: 12px;
  line-height: 1.5;
  color: var(--studio-muted, var(--ink-text-secondary));
}

.selection-rewrite-toolbar__status-bar {
  position: relative;
  display: block;
  width: 100%;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--studio-border, var(--ink-border)) 65%, transparent);
}

.selection-rewrite-toolbar__status-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  width: 45%;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    color-mix(
      in srgb,
      var(--ink-accent, #4f7cff) 55%,
      var(--studio-card-bg, var(--ink-surface-1))
    ),
    var(--ink-accent, #4f7cff)
  );
  animation: selection-rewrite-toolbar-pulse 1.2s ease-in-out infinite;
}

.selection-rewrite-toolbar__button {
  border: 1px solid var(--studio-border, var(--ink-border));
  border-radius: 999px;
  background: var(--studio-surface, var(--ink-surface-2));
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1;
  color: var(--studio-title, var(--ink-text-primary));
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease;
}

.selection-rewrite-toolbar__button:hover:not(:disabled) {
  border-color: var(--ink-accent, var(--ink-primary));
  background: var(--ink-primary-soft, rgba(79, 124, 255, 0.1));
}

.selection-rewrite-toolbar__button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.selection-rewrite-toolbar__button--secondary {
  color: var(--studio-muted, var(--ink-text-secondary));
}

@keyframes selection-rewrite-toolbar-pulse {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(220%);
  }
}
</style>
