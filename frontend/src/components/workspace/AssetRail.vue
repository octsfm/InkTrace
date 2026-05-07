<template>
  <nav class="asset-rail" aria-label="写作资产工具栏">
    <button
      v-for="item in visibleItems"
      :key="item.key"
      type="button"
      class="asset-rail-button"
      :class="{ active: item.key === activeTab }"
      :title="item.label"
      :aria-label="item.label"
      :aria-pressed="item.key === activeTab"
      :data-asset-tab="item.key"
      @click="handleToggle(item.key)"
    >
      <span class="asset-rail-icon" aria-hidden="true">{{ item.icon }}</span>
    </button>
  </nav>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: ''
  },
  hideActiveEntry: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle'])

const items = [
  { key: 'outline', label: '大纲', icon: '纲' },
  { key: 'timeline', label: '时间线', icon: '线' },
  { key: 'foreshadow', label: '伏笔', icon: '伏' },
  { key: 'character', label: '人物', icon: '人' }
]

const visibleItems = computed(() => items.filter((item) => {
  if (!props.hideActiveEntry) return true
  return item.key !== props.activeTab
}))

const handleToggle = (key) => {
  emit('toggle', key === props.activeTab ? '' : key)
}
</script>

<style scoped>
.asset-rail {
  display: grid;
  align-content: start;
  gap: 10px;
}

.asset-rail-button {
  display: grid;
  place-items: center;
  min-height: 60px;
  min-width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 14px;
  background: #ffffff;
  color: #374151;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.asset-rail-button.active {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
}

.asset-rail-icon {
  font-size: 24px;
  line-height: 1;
  font-weight: 700;
}
</style>
