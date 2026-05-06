<template>
  <nav class="asset-rail" aria-label="Writing assets">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      class="asset-rail-button"
      :class="{ active: item.key === activeTab }"
      :aria-pressed="item.key === activeTab"
      :data-asset-tab="item.key"
      @click="handleToggle(item.key)"
    >
      <span class="asset-rail-icon" aria-hidden="true">{{ item.icon }}</span>
      <span class="asset-rail-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<script setup>
const props = defineProps({
  activeTab: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['toggle'])

const items = [
  { key: 'outline', label: 'Outline', icon: 'O' },
  { key: 'timeline', label: 'Timeline', icon: 'T' },
  { key: 'foreshadow', label: 'Foreshadow', icon: 'F' },
  { key: 'character', label: 'Character', icon: 'C' }
]

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
  gap: 4px;
  min-height: 52px;
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
  font-size: 16px;
  line-height: 1;
}

.asset-rail-label {
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
