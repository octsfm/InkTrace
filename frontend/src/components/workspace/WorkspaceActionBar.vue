<template>
  <div class="workspace-action-row">
    <button
      v-for="item in items"
      :key="item.label"
      type="button"
      class="workspace-action-chip"
      :class="{ primary: item.primary }"
      @click="item.onClick?.()"
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
  }
})
</script>

<style scoped>
.workspace-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.workspace-action-chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  color: #4B5563;
  font-size: 12px;
  cursor: pointer;
}

.workspace-action-chip.primary {
  border-color: #BFDBFE;
  background-color: #EFF6FF;
  color: #1D4ED8;
}
</style>
