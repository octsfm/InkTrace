<template>
  <div v-if="visible" class="mention-tooltip" role="tooltip" data-test="mention-tooltip">
    <strong>{{ title }}</strong>
    <p>{{ helperText || '正在读取资料…' }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  visible: { type: Boolean, default: false },
  mention: { type: Object, default: null },
  summary: { type: Object, default: null }
})
const title = computed(() => String(props.summary?.entity_current_name || props.summary?.entity_name_snapshot || props.mention?.entity_name_snapshot || '引用资料'))
const helperText = computed(() => String(props.summary?.helper_text || props.summary?.summary_text || ''))
</script>

<style scoped>
.mention-tooltip { position: absolute; z-index: 5; left: 0; top: calc(100% + 6px); width: min(280px, 70vw); padding: 10px 12px; border: 1px solid var(--ink-border, #dbe3ef); border-radius: 10px; background: var(--ink-surface-1, #fff); color: var(--ink-text-primary, #172033); box-shadow: 0 12px 28px rgb(15 23 42 / 16%); font-size: 12px; line-height: 1.55; white-space: normal; }
.mention-tooltip p { margin: 4px 0 0; color: var(--ink-text-muted, #667085); }
</style>
