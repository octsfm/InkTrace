<template>
  <div class="workspace-selectable-row">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      class="workspace-selectable-chip"
      :class="{ active: selectedKey === item.key }"
      @click="item.onClick?.(item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  },
  selectedKey: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.workspace-selectable-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.workspace-selectable-chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  color: #4B5563;
  font-size: 12px;
  cursor: pointer;
}

.workspace-selectable-chip:hover {
  border-color: #D1D5DB;
}

.workspace-selectable-chip.active {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
  color: #1D4ED8;
}
</style>
