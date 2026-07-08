<template>
  <section class="writing-preference-panel" data-test="writing-preference-panel">
    <div class="panel-header">
      <div>
        <h3>写作阅读偏好</h3>
        <p>这里只调整正文阅读体验,包括字体、字号和行高,不会修改全局界面主题和正文内容。</p>
      </div>
      <button type="button" class="close-button" @click="$emit('close')">关闭</button>
    </div>

    <div class="option-group">
      <span class="option-label">字体</span>
      <div class="chip-row">
        <button
          v-for="item in fontFamilyOptions"
          :key="item.value"
          type="button"
          class="option-chip"
          :class="{ 'option-chip--active': preferences.fontFamily === item.value }"
          :data-test="`font-${item.value}`"
          @click="updatePreference({ fontFamily: item.value })"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <div class="option-group">
      <label class="option-field" for="writing-font-size">
        <span class="option-label">字号</span>
        <select
          id="writing-font-size"
          class="option-select"
          :value="preferences.fontSize"
          data-test="font-size-select"
          @change="updatePreference({ fontSize: Number($event.target.value) })"
        >
          <option v-for="size in fontSizeOptions" :key="size" :value="size">{{ size }} px</option>
        </select>
      </label>
    </div>

    <div class="option-group">
      <label class="option-field" for="writing-line-height">
        <span class="option-label">行高</span>
        <select
          id="writing-line-height"
          class="option-select"
          :value="preferences.lineHeight"
          data-test="line-height-select"
          @change="updatePreference({ lineHeight: Number($event.target.value) })"
        >
          <option v-for="height in lineHeightOptions" :key="height" :value="height">{{ height }}</option>
        </select>
      </label>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  preferences: {
    type: Object,
    default: () => ({
      fontFamily: 'system-ui',
      fontSize: 18,
      lineHeight: 1.8
    })
  }
})

const emit = defineEmits(['update-preferences', 'close'])

const fontFamilyOptions = [
  { label: '系统', value: 'system-ui' },
  { label: '衬线', value: 'serif' },
  { label: '等宽', value: 'monospace' }
]

const fontSizeOptions = [14, 16, 18, 20, 22, 24, 28]
const lineHeightOptions = [1.4, 1.6, 1.8, 2, 2.2]

const preferences = computed(() => ({
  fontFamily: String(props.preferences?.fontFamily || 'system-ui'),
  fontSize: Number(props.preferences?.fontSize || 18),
  lineHeight: Number(props.preferences?.lineHeight || 1.8)
}))

const updatePreference = (patch) => {
  emit('update-preferences', patch)
}
</script>

<style scoped>
.writing-preference-panel {
  border: 1px solid var(--ink-border, #e5e7eb);
  border-radius: 20px;
  background: var(--ink-surface-1, #ffffff);
  padding: 18px 20px;
  display: grid;
  gap: 16px;
  min-width: min(100%, 420px);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-text-primary, #111827);
}

.panel-header p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink-text-muted, #6b7280);
}

.close-button {
  border: none;
  background: transparent;
  color: var(--ink-text-muted, #6b7280);
  font-size: 13px;
  cursor: pointer;
}

.option-group {
  display: grid;
  gap: 10px;
}

.option-field {
  display: grid;
  gap: 10px;
}

.option-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-text-secondary, #374151);
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.option-chip {
  border: 1px solid var(--ink-border-strong, #d1d5db);
  border-radius: 999px;
  background: var(--ink-surface-1, #ffffff);
  padding: 8px 12px;
  font-size: 13px;
  color: var(--ink-text-secondary, #374151);
  cursor: pointer;
}

.option-chip--active {
  border-color: var(--ink-accent, #2563eb);
  background: var(--ink-accent-soft, #eff6ff);
  color: var(--ink-accent, #1d4ed8);
}

.option-select {
  width: 100%;
  border: 1px solid var(--ink-border-strong, #d1d5db);
  border-radius: 12px;
  background: var(--ink-surface-1, #ffffff);
  padding: 10px 12px;
  font-size: 14px;
  color: var(--ink-text-primary, #111827);
}
</style>
