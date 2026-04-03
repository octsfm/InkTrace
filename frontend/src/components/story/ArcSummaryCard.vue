<template>
  <el-alert
    v-if="visibleText"
    :title="visibleText"
    type="info"
    show-icon
    :closable="false"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  planningReason: { type: String, default: '' },
  stageBefore: { type: String, default: '' },
  stageAfterExpected: { type: String, default: '' },
  stageAfterActual: { type: String, default: '' },
  stageAdvanced: { type: Boolean, default: false }
})

const visibleText = computed(() => {
  if (!props.planningReason && !props.stageBefore && !props.stageAfterExpected && !props.stageAfterActual) return ''
  const expected = props.stageBefore || props.stageAfterExpected
    ? `阶段预期：${props.stageBefore || '未知'} -> ${props.stageAfterExpected || '未知'}`
    : ''
  const actual = props.stageAfterActual
    ? `实际阶段：${props.stageBefore || '未知'} -> ${props.stageAfterActual}${props.stageAdvanced ? '（已推进）' : '（未推进）'}`
    : ''
  return `规划原因：${props.planningReason || 'default_light_planning'}${expected ? `；${expected}` : ''}${actual ? `；${actual}` : ''}`
})
</script>
