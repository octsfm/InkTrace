<template>
  <div class="workspace-info-banner" :class="tone">
    {{ text }}
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    required: true
  },
  tone: {
    type: String,
    default: 'neutral'
  }
})
</script>

<style scoped>
.workspace-info-banner {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  font-size: 13px;
  color: #4B5563;
}

.workspace-info-banner.primary {
  border-color: #DBEAFE;
  background-color: #EFF6FF;
  color: #1D4ED8;
  font-weight: 600;
}
</style>
