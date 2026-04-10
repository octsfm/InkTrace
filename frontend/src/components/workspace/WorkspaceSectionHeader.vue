<template>
  <div class="workspace-section-header">
    <div class="workspace-section-main">
      <slot name="main" />
    </div>
    <div v-if="$slots.actions" class="workspace-section-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.workspace-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.workspace-section-main {
  min-width: 0;
}

.workspace-section-main :deep(h2),
.workspace-section-main :deep(h3) {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.workspace-section-main :deep(p) {
  margin: 8px 0 0;
  color: #6B7280;
  font-size: 14px;
  line-height: 1.6;
}

.workspace-section-actions {
  flex-shrink: 0;
}
</style>
