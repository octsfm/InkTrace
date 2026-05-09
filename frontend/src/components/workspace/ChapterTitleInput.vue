﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <label class="chapter-title-input" :class="{ 'chapter-title-input--disabled': disabled }">
    <span class="chapter-title-prefix">{{ chapterPrefix }}</span>
    <input
      :value="inputValue"
      class="chapter-title-field"
      type="text"
      :disabled="disabled"
      :placeholder="placeholder"
      maxlength="120"
      @input="handleInput"
    />
  </label>
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
const inputValue = computed(() => String(props.modelValue || ''))

const handleInput = (event) => {
  emit('update:modelValue', String(event?.target?.value || ''))
}
</script>

<style scoped>
.chapter-title-input {
  display: flex;
  align-items: center;
  gap: 10px;
  width: min(560px, 100%);
  height: 44px;
  box-sizing: border-box;
  min-height: 44px;
  max-height: 44px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  padding: 0 14px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chapter-title-prefix {
  flex: 0 0 auto;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}

.chapter-title-field {
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 16px;
  line-height: 44px;
  font-weight: 600;
  color: #111827;
  outline: none;
  appearance: none;
}

.chapter-title-field::placeholder {
  color: #9ca3af;
}

.chapter-title-input:focus-within {
  border-color: #dbeafe;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

.chapter-title-input--disabled {
  background: #f9fafb;
}

.chapter-title-input--disabled .chapter-title-prefix,
.chapter-title-field:disabled {
  color: #9ca3af;
}
</style>
