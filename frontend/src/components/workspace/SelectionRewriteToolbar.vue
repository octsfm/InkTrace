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
      <span>正在生成，请稍等</span>
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
      清除历史改写
    </button>
  </div>
</template>

<script setup>
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
  border: 1px solid var(--studio-border, #d1d5db);
  border-radius: 16px;
  background: var(--studio-card-bg, #ffffff);
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
  color: var(--studio-muted, #6b7280);
}

.selection-rewrite-toolbar__status-bar {
  position: relative;
  display: block;
  width: 100%;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5e7eb;
}

.selection-rewrite-toolbar__status-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  width: 45%;
  border-radius: inherit;
  background: linear-gradient(90deg, #60a5fa, #2563eb);
  animation: selection-rewrite-toolbar-pulse 1.2s ease-in-out infinite;
}

.selection-rewrite-toolbar__button {
  border: 1px solid var(--studio-border, #d1d5db);
  border-radius: 999px;
  background: var(--studio-card-bg, #ffffff);
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1;
  color: var(--studio-title, #111827);
  cursor: pointer;
}

.selection-rewrite-toolbar__button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.selection-rewrite-toolbar__button--secondary {
  color: var(--studio-muted, #6b7280);
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
