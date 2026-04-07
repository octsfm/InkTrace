<template>
  <el-form-item label="目标剧情弧">
    <el-select :model-value="modelValue" placeholder="自动选择" style="width: 220px" clearable @update:model-value="handleChange">
      <el-option
        v-for="arc in arcs"
        :key="arc.arc_id"
        :label="formatArcLabel(arc)"
        :value="arc.arc_id"
      />
    </el-select>
  </el-form-item>
</template>

<script setup>
import { ARC_STAGE_LABELS, ARC_TYPE_LABELS } from '@/constants/storyLabels'

const props = defineProps({
  modelValue: { type: String, default: '' },
  arcs: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const handleChange = (value) => {
  emit('update:modelValue', value || '')
}

const formatArcLabel = (arc) => {
  const rawTitle = String(arc?.title || '').trim()
  const title = rawTitle && !/main story arc|character arc|supporting pressure arc|supporting world arc/i.test(rawTitle)
    ? rawTitle
    : ({
        main_arc: '主线推进弧',
        character_arc: '人物成长弧',
        supporting_arc: '支线压力弧',
      }[arc?.arc_type] || arc?.arc_id || '未命名剧情弧')
  const stageLabel = ARC_STAGE_LABELS[arc?.current_stage] || ''
  const typeLabel = ARC_TYPE_LABELS[arc?.arc_type] || ''
  const stage = stageLabel ? ` · ${stageLabel}` : ''
  const type = typeLabel ? ` · ${typeLabel}` : ''
  return `${title}${type}${stage}`
}
</script>
