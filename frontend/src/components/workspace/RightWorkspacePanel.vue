<template>
  <aside
    class="right-workspace-panel"
    :class="{
      'right-workspace-panel--expanded': isExpanded,
      'right-workspace-panel--mobile': mobile
    }"
    :style="panelStyle"
    aria-label="右侧资料与 AI 工作区"
  >
    <div class="right-workspace-panel__tab-rail" role="tablist" aria-label="工作区标签">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="right-workspace-panel__tab-button"
        :class="{ 'is-active': item.key === modelValue }"
        :aria-label="item.label"
        :aria-pressed="item.key === modelValue"
        :data-workspace-tab="item.key"
        @click="handleTabClick(item.key)"
      >
        <span class="right-workspace-panel__tab-icon" aria-hidden="true">{{ item.icon }}</span>
        <span v-if="isExpanded" class="right-workspace-panel__tab-label">{{ item.label }}</span>
      </button>
    </div>

    <div v-if="isExpanded" class="right-workspace-panel__surface">
      <button
        type="button"
        class="right-workspace-panel__resizer"
        aria-label="调整右侧工作区宽度"
        @mousedown.prevent="handleResizeStart"
      />
      <header class="right-workspace-panel__header">
        <div>
          <h3>{{ activeItem.label }}</h3>
          <p>{{ activeItem.description }}</p>
        </div>
        <button type="button" class="right-workspace-panel__close" @click="$emit('update:modelValue', '')">收起</button>
      </header>

      <div class="right-workspace-panel__body">
        <slot :active-tab="modelValue" />
      </div>

      <div v-if="pendingAction" class="right-workspace-panel__dirty-guard" role="dialog" aria-modal="true">
        <div class="right-workspace-panel__dirty-card">
          <h4>存在未保存修改</h4>
          <p>请先保存或放弃当前修改，再继续切换右侧工作区。</p>
          <div class="right-workspace-panel__dirty-actions">
            <button data-test="workspace-dirty-save" type="button" @click="confirmSave">保存</button>
            <button data-test="workspace-dirty-discard" type="button" @click="confirmDiscard">放弃</button>
            <button data-test="workspace-dirty-cancel" type="button" @click="cancelPending">取消</button>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const MIN_WIDTH = 320
const ABSOLUTE_MAX_WIDTH = 760
const DEFAULT_WIDTH = 360

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  dirtyTabs: {
    type: Array,
    default: () => []
  },
  mobile: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'update:model-value', 'save-dirty', 'discard-dirty', 'width-change'])

const items = [
    { key: 'outline', label: '大纲', icon: '纲', description: '查看全书与当前章节大纲。' },
    { key: 'timeline', label: '线索', icon: '线', description: '查看时间线与关键事件。' },
    { key: 'foreshadow', label: '伏笔', icon: '伏', description: '维护伏笔与回收计划。' },
    { key: 'character', label: '人物', icon: '人', description: '查看角色设定与状态。' },
    { key: 'ai', label: 'AI', icon: 'AI', description: '查看生成链路、会话进度与上下文状态。' },
    { key: 'review', label: '审阅', icon: '审', description: '查看候选稿、审阅结果、冲突和记忆门控。' }
]

const pendingAction = ref(null)
const panelWidth = ref(DEFAULT_WIDTH)
let teardownResize = null
let teardownKeyboard = null
let teardownWindowResize = null

const resolveMaxWidth = () => {
  if (typeof window === 'undefined') {
    return ABSOLUTE_MAX_WIDTH
  }
  const viewportBound = Math.max(MIN_WIDTH, Math.floor(window.innerWidth * 0.6))
  return Math.min(ABSOLUTE_MAX_WIDTH, viewportBound)
}

const clampWidth = (value) => {
  const numeric = Number(value || DEFAULT_WIDTH)
  const maxWidth = resolveMaxWidth()
  return Math.min(maxWidth, Math.max(MIN_WIDTH, numeric))
}

const isExpanded = computed(() => Boolean(props.modelValue))
const activeItem = computed(() => (
  items.find((item) => item.key === props.modelValue) ||
  items.find((item) => item.key === 'outline')
))
const panelStyle = computed(() => (
  isExpanded.value
    ? { '--workspace-panel-width': `${panelWidth.value}px` }
    : { '--workspace-panel-width': '48px' }
))

const isCurrentDirty = computed(() => props.dirtyTabs.includes(props.modelValue))

const finishPending = () => {
  const action = pendingAction.value
  pendingAction.value = null
  if (!action) return
  emit('update:modelValue', action.nextTab)
}

const confirmSave = () => {
  emit('save-dirty', props.modelValue)
  finishPending()
}

const confirmDiscard = () => {
  emit('discard-dirty', props.modelValue)
  finishPending()
}

const cancelPending = () => {
  pendingAction.value = null
}

const handleTabClick = (tabKey) => {
  const nextTab = String(tabKey || '')
  if (!nextTab) return
  if (nextTab === props.modelValue) {
    emit('update:modelValue', '')
    return
  }
  if (isCurrentDirty.value) {
    pendingAction.value = { nextTab }
    return
  }
  emit('update:modelValue', nextTab)
}

const handleResizeStart = (event) => {
  if (props.mobile || typeof window === 'undefined') return
  const originX = Number(event?.clientX || 0)
  const originWidth = panelWidth.value
  const handleMove = (moveEvent) => {
    const delta = originX - Number(moveEvent.clientX || 0)
    panelWidth.value = clampWidth(originWidth + delta)
  }
  const handleUp = () => {
    window.removeEventListener('mousemove', handleMove)
    window.removeEventListener('mouseup', handleUp)
    teardownResize = null
  }
  teardownResize = handleUp
  window.addEventListener('mousemove', handleMove)
  window.addEventListener('mouseup', handleUp)
}

const handleKeydown = (event) => {
  if (event?.key !== 'Escape') return
  if (!props.modelValue) return
  if (pendingAction.value) {
    pendingAction.value = null
    return
  }
  emit('update:modelValue', '')
}

const handleWindowResize = () => {
  const nextWidth = clampWidth(panelWidth.value)
  if (nextWidth === panelWidth.value) return
  panelWidth.value = nextWidth
}

watch(panelWidth, (nextWidth) => {
  emit('width-change', nextWidth)
})

onMounted(() => {
  panelWidth.value = clampWidth(panelWidth.value)
  emit('width-change', panelWidth.value)
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', handleKeydown)
    window.addEventListener('resize', handleWindowResize)
    teardownKeyboard = () => window.removeEventListener('keydown', handleKeydown)
    teardownWindowResize = () => window.removeEventListener('resize', handleWindowResize)
  }
})

watch(
  () => props.modelValue,
  () => {
    panelWidth.value = clampWidth(panelWidth.value)
  }
)

onBeforeUnmount(() => {
  teardownResize?.()
  teardownKeyboard?.()
  teardownWindowResize?.()
})
</script>

<style scoped>
.right-workspace-panel {
  --workspace-panel-border: var(--studio-border, var(--ink-border, #e5e7eb));
  --workspace-panel-bg: var(--studio-card-bg, var(--ink-surface-1, #ffffff));
  --workspace-panel-bg-soft: var(--studio-bg-focus, var(--ink-surface-2, #f8fafc));
  --workspace-panel-title: var(--studio-title, var(--ink-text-primary, #111827));
  --workspace-panel-text: var(--studio-text, var(--ink-text-secondary, #6b7280));
  --workspace-panel-muted: var(--studio-muted, var(--ink-text-muted, #9ca3af));

  position: relative;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  width: var(--workspace-panel-width, 48px);
  border: 1px solid var(--workspace-panel-border);
  border-radius: 22px;
  background: var(--workspace-panel-bg);
  overflow: hidden;
}

.right-workspace-panel--mobile {
  width: 100%;
}

.right-workspace-panel__tab-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
  border-right: 1px solid var(--workspace-panel-border);
  background: var(--workspace-panel-bg);
}

.right-workspace-panel__tab-button {
  width: 100%;
  min-height: 52px;
  display: grid;
  place-items: center;
  gap: 4px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: transparent;
  color: var(--workspace-panel-text);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.right-workspace-panel__tab-button.is-active {
  background: var(--workspace-panel-bg-soft);
  border-color: var(--workspace-panel-border);
  color: var(--workspace-panel-title);
}

.right-workspace-panel__tab-icon {
  font-size: 15px;
  line-height: 1;
}

.right-workspace-panel__tab-label {
  font-size: 12px;
}

.right-workspace-panel__surface {
  position: relative;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background: var(--workspace-panel-bg);
}

.right-workspace-panel__resizer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 8px;
  border: 0;
  background: transparent;
  cursor: col-resize;
}

.right-workspace-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--workspace-panel-border);
}

.right-workspace-panel__header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--workspace-panel-title);
}

.right-workspace-panel__header p {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--workspace-panel-text);
}

.right-workspace-panel__close {
  border: 1px solid var(--workspace-panel-border);
  border-radius: 999px;
  background: var(--workspace-panel-bg);
  color: var(--workspace-panel-title);
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.right-workspace-panel__body {
  min-height: 0;
  overflow: auto;
  padding: 18px;
  background: var(--workspace-panel-bg);
}

.right-workspace-panel__dirty-guard {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.28);
  padding: 20px;
}

.right-workspace-panel__dirty-card {
  width: min(320px, 100%);
  border: 1px solid var(--workspace-panel-border);
  border-radius: 20px;
  background: var(--workspace-panel-bg);
  padding: 18px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.18);
}

.right-workspace-panel__dirty-card h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--workspace-panel-title);
}

.right-workspace-panel__dirty-card p {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--workspace-panel-text);
}

.right-workspace-panel__dirty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.right-workspace-panel__dirty-actions button {
  border: 1px solid var(--workspace-panel-border);
  border-radius: 999px;
  background: var(--workspace-panel-bg-soft);
  color: var(--workspace-panel-title);
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
</style>
