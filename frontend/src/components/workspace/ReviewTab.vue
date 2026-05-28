<template>
  <AIPanel
    :work-id="workId"
    :chapter-id="chapterId"
    :chapter-version="chapterVersion"
    :developer-mode="developerMode"
    mode="review"
  />
</template>

<script setup>
import AIPanel from './AIPanel.vue'

defineProps({
  workId: {
    type: String,
    default: ''
  },
  chapterId: {
    type: String,
    default: ''
  },
  chapterVersion: {
    type: Number,
    default: 0
  },
  developerMode: {
    type: Boolean,
    default: false
  }
})
</script>
