<template>
  <div class="workspace-summary-row" :class="variant">
    <div
      v-for="item in items"
      :key="item.label"
      class="workspace-summary-chip"
    >
      <span class="workspace-summary-label">{{ item.label }}</span>
      <span class="workspace-summary-value">{{ item.value }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  },
  variant: {
    type: String,
    default: 'default'
  }
})
</script>

<style scoped>
.workspace-summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.workspace-summary-chip {
  min-width: 96px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.workspace-summary-label {
  display: block;
  font-size: 11px;
  color: #9CA3AF;
}

.workspace-summary-value {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.workspace-summary-row.compact .workspace-summary-chip {
  min-width: 120px;
  background-color: #FFFFFF;
}

.workspace-summary-row.compact .workspace-summary-value {
  font-size: 13px;
}
</style>
