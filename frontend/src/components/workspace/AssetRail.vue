<template>
  <nav class="asset-rail" aria-label="结构化资产入口">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      class="asset-rail-button"
      :class="{ active: item.key === activeTab }"
      @click="$emit('toggle', item.key)"
    >
      {{ item.label }}
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

defineEmits(['toggle'])

const items = [
  { key: 'outline', label: '纲' },
  { key: 'timeline', label: '线' },
  { key: 'foreshadow', label: '伏' },
  { key: 'character', label: '人' }
]
</script>

<style scoped>
.asset-rail {
  display: grid;
  align-content: start;
  gap: 10px;
}

.asset-rail-button {
  min-height: 44px;
  border: 1px solid #d1d5db;
  border-radius: 14px;
  background: #ffffff;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.asset-rail-button.active {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
}
</style>
