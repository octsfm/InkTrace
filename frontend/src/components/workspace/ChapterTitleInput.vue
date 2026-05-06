﻿﻿﻿﻿﻿<template>
  <input
    :value="displayValue"
    class="chapter-title-input"
    type="text"
    :disabled="disabled"
    :placeholder="placeholder"
    maxlength="120"
    @input="handleInput"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  orderIndex: {
    type: Number,
    default: 1
  },
  disabled: {
    type: Boolean,
    default: false
  },
  placeholder: {
    type: String,
    default: '输入章节标题'
  }
})

const emit = defineEmits(['update:modelValue'])

const chapterPrefix = computed(() => `第${Number(props.orderIndex || 1)}章`)
const displayValue = computed(() => {
  const title = String(props.modelValue || '').trim()
  return title ? `${chapterPrefix.value} ${title}` : chapterPrefix.value
})

const stripChapterPrefix = (value) => {
  return String(value || '')
    .replace(/^\s*第\s*\d+\s*章\s*/u, '')
    .trim()
}

const handleInput = (event) => {
  emit('update:modelValue', stripChapterPrefix(event?.target?.value))
}
</script>

<style scoped>
.chapter-title-input {
  display: block;
  width: min(560px, 100%);
  height: 44px;
  box-sizing: border-box;
  min-height: 44px;
  max-height: 44px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: #ffffff;
  padding: 0 14px;
  font-size: 16px;
  line-height: 44px;
  font-weight: 600;
  text-align: center;
  color: #111827;
  outline: none;
  appearance: none;
}

.chapter-title-input::placeholder {
  color: #9ca3af;
}

.chapter-title-input:focus {
  border-color: #dbeafe;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

.chapter-title-input:disabled {
  color: #9ca3af;
}
</style>
