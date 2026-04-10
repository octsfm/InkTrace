<template>
  <div class="hero-chip-row">
    <div
      v-for="item in items"
      :key="item.label"
      class="hero-chip"
    >
      <span class="chip-label">{{ item.label }}</span>
      <span class="chip-value">{{ item.value }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.hero-chip-row {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.hero-chip {
  min-width: 124px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: rgba(255, 255, 255, 0.88);
}

.chip-label {
  display: block;
  font-size: 11px;
  color: #9CA3AF;
}

.chip-value {
  display: block;
  margin-top: 4px;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}
</style>
