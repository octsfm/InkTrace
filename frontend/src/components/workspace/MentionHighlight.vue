<template>
  <div class="mention-highlight" aria-hidden="true">
    <template v-for="segment in segments" :key="segment.key"><span v-if="!segment.mention">{{ segment.text }}</span><span v-else class="mention-highlight__item" :class="itemClasses(segment.mention)" :data-mention-id="segment.mention.mention_id" @mouseenter="activate(segment.mention)" @mouseleave="deactivate">{{ segment.text }}<MentionTooltip :visible="activeMentionId === segment.mention.mention_id" :mention="segment.mention" :summary="summaryById[segment.mention.mention_id]" /></span></template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import MentionTooltip from './MentionTooltip.vue'
const props = defineProps({ content: { type: String, default: '' }, mentions: { type: Array, default: () => [] }, summaryById: { type: Object, default: () => ({}) } })
const emit = defineEmits(['mention-hover'])
const activeMentionId = ref('')
let hoverTimer = null
const segments = computed(() => {
  const content = String(props.content || '')
  const valid = [...props.mentions].filter((item) => item && item.status !== 'broken' && Number(item.end_pos) > Number(item.start_pos)).filter((item) => Number(item.start_pos) >= 0 && Number(item.end_pos) <= content.length).sort((a, b) => Number(a.start_pos) - Number(b.start_pos))
  const result = []
  let cursor = 0
  valid.forEach((mention, index) => {
    const start = Number(mention.start_pos); const end = Number(mention.end_pos)
    if (start < cursor) return
    if (start > cursor) result.push({ key: `text-${index}-${cursor}`, text: content.slice(cursor, start), mention: null })
    result.push({ key: `mention-${mention.mention_id || index}-${start}`, text: content.slice(start, end), mention })
    cursor = end
  })
  if (cursor < content.length) result.push({ key: `text-tail-${cursor}`, text: content.slice(cursor), mention: null })
  return result
})
const itemClasses = (mention) => [`mention-highlight__item--${mention.source === 'ai_suggestion' ? 'ai' : 'user'}`, { 'mention-highlight__item--inactive': mention.status === 'inactive_entity' }]
const activate = (mention) => { clearTimeout(hoverTimer); hoverTimer = setTimeout(() => { activeMentionId.value = String(mention?.mention_id || ''); if (activeMentionId.value) emit('mention-hover', mention) }, 500) }
const deactivate = () => { clearTimeout(hoverTimer); activeMentionId.value = '' }
</script>

<style scoped>
.mention-highlight { color: transparent; white-space: pre-wrap; overflow-wrap: break-word; pointer-events: none; }
.mention-highlight__item { position: relative; color: transparent; pointer-events: auto; }
.mention-highlight__item--user { background: rgb(59 130 246 / 15%); border-bottom: 1px solid #3b82f6; }
.mention-highlight__item--ai { border-bottom: 1px dashed #8b5cf6; }
.mention-highlight__item--inactive { background: rgb(148 163 184 / 18%); border-color: #94a3b8; }
</style>
