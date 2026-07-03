<template>
  <div
    v-if="visible"
    class="selection-rewrite-toolbar"
    data-test="selection-rewrite-toolbar"
  >
    <button
      v-for="item in modeOptions"
      :key="item.id"
      type="button"
      class="selection-rewrite-toolbar__button"
      :data-test="`selection-rewrite-mode-${item.id}`"
      @click="$emit('mode-select', item.id)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

defineEmits(['mode-select'])

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
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--studio-border, #d1d5db);
  border-radius: 16px;
  background: var(--studio-card-bg, #ffffff);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
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
</style>
