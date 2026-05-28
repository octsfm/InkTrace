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
const MAX_WIDTH = 480
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

const emit = defineEmits(['update:modelValue', 'save-dirty', 'discard-dirty', 'width-change'])

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
    panelWidth.value = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, originWidth + delta))
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

watch(panelWidth, (nextWidth) => {
  emit('width-change', nextWidth)
})

onMounted(() => {
  emit('width-change', panelWidth.value)
})

onBeforeUnmount(() => {
  teardownResize?.()
})
</script>

<style scoped>
.right-workspace-panel {
  --workspace-panel-width: 48px;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  width: var(--workspace-panel-width);
  min-width: 48px;
  height: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-panel-background);
  overflow: hidden;
  transition: width 180ms ease;
}

.right-workspace-panel--expanded {
  grid-template-columns: minmax(0, 1fr);
}

.right-workspace-panel--expanded .right-workspace-panel__tab-rail {
  display: none;
}

.right-workspace-panel--mobile {
  width: min(100%, 100vw - var(--space-8));
}

.right-workspace-panel__tab-rail {
  display: grid;
  align-content: start;
  gap: var(--space-2);
  padding: var(--space-2);
  border-right: 1px solid var(--color-border);
  background: var(--color-panel-background);
}

.right-workspace-panel__tab-button {
  display: grid;
  place-items: center;
  gap: var(--space-1);
  min-height: 48px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.right-workspace-panel__tab-button.is-active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.right-workspace-panel__tab-icon {
  font-size: var(--text-md);
  font-weight: 700;
}

.right-workspace-panel__tab-label {
  font-size: var(--text-xs);
  font-weight: 600;
}

.right-workspace-panel__surface {
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: var(--color-background);
}

.right-workspace-panel__resizer {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 10px;
  border: none;
  background: linear-gradient(
    90deg,
    rgba(79, 124, 255, 0.28) 0,
    rgba(79, 124, 255, 0.12) 30%,
    rgba(79, 124, 255, 0) 100%
  );
  opacity: 0;
  cursor: ew-resize;
  z-index: 3;
  transition: opacity 140ms ease;
}

.right-workspace-panel__surface:hover .right-workspace-panel__resizer {
  opacity: 1;
}

.right-workspace-panel__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.right-workspace-panel__header h3 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-lg);
}

.right-workspace-panel__header p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.right-workspace-panel__close,
.right-workspace-panel__dirty-actions button {
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-pill);
  background: var(--color-background);
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
}

.right-workspace-panel__body {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-4);
}

.right-workspace-panel__dirty-guard {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(31, 41, 51, 0.24);
}

.right-workspace-panel__dirty-card {
  width: min(320px, calc(100% - var(--space-8)));
  border-radius: var(--radius-md);
  background: var(--color-background);
  padding: var(--space-4);
  box-shadow: var(--shadow-dialog);
}

.right-workspace-panel__dirty-card h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-md);
}

.right-workspace-panel__dirty-card p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.right-workspace-panel__dirty-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
</style>
