<template>
  <section class="state-panel" :class="toneClass">
    <div class="state-copy">
      <div class="state-top">
        <span class="state-tag">{{ resolvedTag }}</span>
        <span v-if="caption" class="state-caption">{{ caption }}</span>
      </div>
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
    </div>

    <div v-if="actions.length" class="state-actions">
      <el-button
        v-for="item in actions"
        :key="item.key"
        :type="item.primary ? 'primary' : undefined"
        :plain="item.primary ? false : true"
        size="small"
        @click="$emit('action', item.key)"
      >
        {{ item.label }}
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tone: {
    type: String,
    default: 'info'
  },
  tag: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  caption: {
    type: String,
    default: ''
  },
  actions: {
    type: Array,
    default: () => []
  }
})

defineEmits(['action'])

const toneClass = computed(() => `tone-${props.tone || 'info'}`)
const resolvedTag = computed(() => {
  if (props.tag) return props.tag
  const tagMap = {
    info: '提示',
    success: '正常',
    warning: '待处理',
    danger: '异常'
  }
  return tagMap[props.tone] || '提示'
})
</script>

<style scoped>
.state-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
}

.state-panel.tone-info {
  border-color: #BFDBFE;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
}

.state-panel.tone-success {
  border-color: #BBF7D0;
  background: linear-gradient(180deg, #FFFFFF 0%, #F0FDF4 100%);
}

.state-panel.tone-warning {
  border-color: #FDE68A;
  background: linear-gradient(180deg, #FFFFFF 0%, #FFFBEB 100%);
}

.state-panel.tone-danger {
  border-color: #FECACA;
  background: linear-gradient(180deg, #FFFFFF 0%, #FEF2F2 100%);
}

.state-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.state-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.state-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background-color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
  font-weight: 600;
  color: #1D4ED8;
}

.state-caption {
  font-size: 12px;
  color: #6B7280;
}

.state-copy h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.state-copy p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.state-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .state-panel {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
