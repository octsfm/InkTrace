<template>
  <aside class="copilot-panel">
    <div class="copilot-header">
      <div>
        <div class="eyebrow">AI Copilot</div>
        <h3>作者助手</h3>
      </div>
      <el-tag size="small" type="success">工作中</el-tag>
    </div>

    <div class="tab-switcher">
      <button
        v-for="item in tabs"
        :key="item"
        type="button"
        class="tab-button"
        :class="{ active: modelValue === item }"
        @click="$emit('update:modelValue', item)"
      >
        {{ tabLabelMap[item] }}
      </button>
    </div>

    <div v-if="modelValue === 'chat'" class="panel-section">
      <div class="panel-card">
        <div class="panel-title">统一助手入口</div>
        <p class="panel-text">
          第一阶段先提供快捷动作和上下文面板。自由对话入口会在下一阶段接入统一的 AuthorAgent。
        </p>
      </div>
      <div class="quick-actions">
        <button
          v-for="action in quickActions"
          :key="action.key"
          type="button"
          class="quick-action"
          @click="$emit('trigger', action.key)"
        >
          <span class="quick-action-title">{{ action.title }}</span>
          <span class="quick-action-desc">{{ action.description }}</span>
        </button>
      </div>
    </div>

    <div v-else-if="modelValue === 'context'" class="panel-section">
      <div class="info-grid">
        <div class="panel-card">
          <div class="panel-title">当前状态</div>
          <p class="panel-text">{{ progressText }}</p>
        </div>
        <div class="panel-card">
          <div class="panel-title">当前进度</div>
          <p class="panel-text">{{ currentProgress }}</p>
        </div>
      </div>
      <div class="panel-card">
        <div class="panel-title">活跃剧情弧</div>
        <div v-if="activeArcs.length" class="arc-list">
          <div v-for="arc in activeArcs.slice(0, 4)" :key="arc.arc_id" class="arc-item">
            <div class="arc-title">{{ arc.title || arc.arc_id }}</div>
            <div class="arc-meta">{{ arc.stage || '未标注阶段' }} · {{ arc.priority || '未标注优先级' }}</div>
          </div>
        </div>
        <p v-else class="panel-text">当前还没有可用的活跃剧情弧。</p>
      </div>
    </div>

    <div v-else class="panel-section">
      <div
        v-for="suggestion in suggestedActions"
        :key="suggestion.key"
        class="panel-card suggestion-card"
      >
        <div class="panel-title">{{ suggestion.title }}</div>
        <p class="panel-text">{{ suggestion.description }}</p>
        <button type="button" class="suggestion-button" @click="$emit('trigger', suggestion.key)">
          {{ suggestion.cta }}
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'context'
  },
  activeArcs: {
    type: Array,
    default: () => []
  },
  memoryView: {
    type: Object,
    default: () => ({})
  },
  organizeProgress: {
    type: Object,
    default: () => ({})
  },
  suggestedActions: {
    type: Array,
    default: () => []
  }
})

defineEmits(['update:modelValue', 'trigger'])

const tabs = ['chat', 'context', 'inspire']
const tabLabelMap = {
  chat: '助手',
  context: '上下文',
  inspire: '灵感'
}

const quickActions = [
  {
    key: 'writing',
    title: '继续写作',
    description: '回到当前章节，继续推进正文。'
  },
  {
    key: 'structure',
    title: '查看结构',
    description: '打开 Story Model 和剧情弧的结构视图。'
  },
  {
    key: 'tasks',
    title: '查看任务',
    description: '查看当前整理、重建或审查任务状态。'
  }
]

const progressText = computed(() => {
  const status = String(props.organizeProgress?.status || '').trim()
  if (!status) return '当前没有正在执行的后台整理任务。'
  if (status === 'running') {
    return `正在整理中，进度 ${props.organizeProgress?.progress ?? 0}%`
  }
  if (status === 'success' || status === 'done') {
    return '最近一次整理已完成。'
  }
  if (status === 'failed' || status === 'error') {
    return props.organizeProgress?.error_message || '最近一次整理失败。'
  }
  return `当前状态：${status}`
})

const currentProgress = computed(() => {
  return (
    props.memoryView?.current_progress ||
    props.memoryView?.current_state ||
    '系统正在等待你决定下一步。'
  )
})
</script>

<style scoped>
.copilot-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  padding: 20px 18px;
  background:
    radial-gradient(circle at top right, rgba(196, 115, 53, 0.12), transparent 32%),
    linear-gradient(180deg, #fbf7f0 0%, #f4eee4 100%);
  border-left: 1px solid rgba(76, 59, 40, 0.08);
}

.copilot-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a66f3e;
}

.copilot-header h3 {
  margin-top: 4px;
  font-size: 20px;
  color: #38281e;
}

.tab-switcher {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.tab-button,
.quick-action,
.suggestion-button {
  border: none;
  background: none;
  font: inherit;
}

.tab-button {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.8);
  color: #72553a;
  cursor: pointer;
}

.tab-button.active {
  background: #fffdf9;
  color: #38281e;
  box-shadow: 0 10px 26px rgba(109, 78, 38, 0.12);
}

.panel-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow: auto;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.panel-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 12px 30px rgba(91, 62, 24, 0.08);
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #38281e;
}

.panel-text {
  margin-top: 8px;
  color: #705946;
  line-height: 1.65;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quick-action {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.quick-action:hover,
.suggestion-button:hover {
  transform: translateY(-1px);
}

.quick-action-title {
  font-weight: 700;
  color: #3d2c1f;
}

.quick-action-desc {
  color: #7e6650;
  line-height: 1.5;
}

.arc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}

.arc-item {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(244, 235, 222, 0.9);
}

.arc-title {
  font-weight: 600;
  color: #3d2c1f;
}

.arc-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #8c6b50;
}

.suggestion-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.suggestion-button {
  align-self: flex-start;
  padding: 8px 12px;
  border-radius: 999px;
  background: #b96429;
  color: #fff8f0;
  cursor: pointer;
}
</style>
