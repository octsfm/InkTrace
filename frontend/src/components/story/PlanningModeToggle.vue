<template>
  <el-form-item label="规划模式">
    <el-radio-group :model-value="modelValue" @update:model-value="handleChange">
      <el-radio label="light_planning">轻规划</el-radio>
      <el-radio label="deep_planning">重规划</el-radio>
    </el-radio-group>
  </el-form-item>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    default: 'light_planning'
  }
})

const emit = defineEmits(['update:modelValue'])

const handleChange = (value) => {
  emit('update:modelValue', value || 'light_planning')
}
</script>
