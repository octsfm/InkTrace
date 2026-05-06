<template>
  <aside
    v-if="visible"
    class="asset-drawer"
    :class="{ 'mobile-overlay': mobile }"
    aria-label="Writing asset drawer"
  >
    <div class="asset-drawer-header">
      <div>
        <h3>{{ activeLabel }}</h3>
        <p>Structured assets are edited here and saved explicitly.</p>
      </div>
      <button type="button" class="close-button" @click="requestClose">Close</button>
    </div>

    <div class="asset-drawer-tabs" role="tablist" aria-label="Writing asset tabs">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="asset-tab"
        :class="{ active: item.key === activeTab }"
        :aria-selected="item.key === activeTab"
        :data-asset-tab="item.key"
        role="tab"
        @click="requestSwitch(item.key)"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="asset-drawer-body">
      <slot :active-tab="activeTab">
        <p class="placeholder">{{ activeLabel }} panel is ready for explicit-save editing.</p>
      </slot>
    </div>

    <div v-if="pendingAction" class="dirty-guard" role="dialog" aria-modal="true">
      <div class="dirty-guard-card">
        <h4>Unsaved asset changes</h4>
        <p>Save or discard the current asset changes before continuing.</p>
        <div class="dirty-guard-actions">
          <button type="button" @click="confirmSave">Save</button>
          <button type="button" @click="confirmDiscard">Discard</button>
          <button type="button" @click="cancelPendingAction">Cancel</button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  activeTab: {
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

const emit = defineEmits(['close', 'switch', 'save-dirty', 'discard-dirty'])

const items = [
  { key: 'outline', label: 'Outline' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'foreshadow', label: 'Foreshadow' },
  { key: 'character', label: 'Character' }
]

const pendingAction = ref(null)

const activeLabel = computed(() => (
  items.find((item) => item.key === props.activeTab)?.label || 'Writing Asset'
))

const isCurrentDirty = computed(() => props.dirtyTabs.includes(props.activeTab))

const requestClose = () => {
  if (isCurrentDirty.value) {
    pendingAction.value = { type: 'close' }
    return
  }
  emit('close')
}

const requestSwitch = (tabKey) => {
  const nextTab = String(tabKey || '')
  if (!nextTab || nextTab === props.activeTab) return
  if (isCurrentDirty.value) {
    pendingAction.value = { type: 'switch', tab: nextTab }
    return
  }
  emit('switch', nextTab)
}

const finishPendingAction = () => {
  const action = pendingAction.value
  pendingAction.value = null
  if (!action) return
  if (action.type === 'close') {
    emit('close')
    return
  }
  if (action.type === 'switch') {
    emit('switch', action.tab)
  }
}

const confirmSave = () => {
  emit('save-dirty', props.activeTab)
  finishPendingAction()
}

const confirmDiscard = () => {
  emit('discard-dirty', props.activeTab)
  finishPendingAction()
}

const cancelPendingAction = () => {
  pendingAction.value = null
}
</script>

<style scoped>
.asset-drawer {
  position: relative;
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #ffffff;
  padding: 18px;
}

.asset-drawer.mobile-overlay {
  position: fixed;
  inset: 0;
  z-index: 40;
  border-radius: 0;
}

.asset-drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.asset-drawer-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.asset-drawer-header p,
.placeholder {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #6b7280;
}

.close-button,
.asset-tab,
.dirty-guard-actions button {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #ffffff;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.asset-drawer-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.asset-tab.active {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
}

.asset-drawer-body {
  margin-top: 18px;
}

.dirty-guard {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: inherit;
  background: rgba(17, 24, 39, 0.24);
}

.dirty-guard-card {
  width: min(320px, calc(100% - 32px));
  border-radius: 18px;
  background: #ffffff;
  padding: 18px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
}

.dirty-guard-card h4 {
  margin: 0;
  font-size: 16px;
  color: #111827;
}

.dirty-guard-card p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.dirty-guard-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
