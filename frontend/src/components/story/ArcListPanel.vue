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
const props = defineProps({
  modelValue: { type: String, default: '' },
  arcs: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const handleChange = (value) => {
  emit('update:modelValue', value || '')
}

const formatArcLabel = (arc) => {
  const title = arc?.title || arc?.arc_id || '未命名剧情弧'
  const stage = arc?.current_stage ? ` · ${arc.current_stage}` : ''
  const priority = arc?.priority ? ` · ${arc.priority}` : ''
  return `${title}${stage}${priority}`
}
</script>
