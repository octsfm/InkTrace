<template>
  <div class="workspace-value-grid" :class="variant">
    <article
      v-for="item in items"
      :key="item.label"
      class="workspace-value-card"
    >
      <div class="workspace-value-label">{{ item.label }}</div>
      <div class="workspace-value-number">{{ item.value }}</div>
      <div class="workspace-value-meta">{{ item.meta }}</div>
    </article>
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
.workspace-value-grid {
  display: grid;
  gap: 16px;
}

.workspace-value-grid.default {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.workspace-value-grid.compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workspace-value-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.workspace-value-label {
  font-size: 12px;
  color: #9CA3AF;
}

.workspace-value-number {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.workspace-value-meta {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: #6B7280;
}

.workspace-value-grid.compact .workspace-value-number {
  margin-top: 12px;
  font-size: 32px;
}
</style>
