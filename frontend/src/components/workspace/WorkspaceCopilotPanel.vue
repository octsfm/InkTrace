<template>
  <aside class="copilot-panel">
    <div class="copilot-header">
      <div class="header-info">
        <div class="header-mark">
          <el-icon class="header-icon"><Cpu /></el-icon>
        </div>
        <div>
          <div class="header-eyebrow">Copilot</div>
          <h3>AI Copilot</h3>
        </div>
      </div>
      <el-tag size="small" type="success" effect="plain">Ready</el-tag>
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

    <!-- Chat Tab -->
    <div v-if="modelValue === 'chat'" class="panel-section chat-section">
      <div class="chat-placeholder">
        <el-icon class="placeholder-icon"><ChatDotRound /></el-icon>
        <p>你可以直接问我：</p>
        <ul class="suggestion-list">
          <li>"上一次主角和反派冲突在哪一章？"</li>
          <li>"下一章最适合推进哪条剧情弧？"</li>
          <li>"这个角色最近的状态是什么？"</li>
        </ul>
        <p class="sub-text">（对话助手正在接入中）</p>
      </div>
    </div>

    <!-- Context Tab -->
    <div v-else-if="modelValue === 'context'" class="panel-section context-section">
      <div class="context-card">
        <div class="card-title">当前状态</div>
        <p class="card-text">{{ progressText }}</p>
      </div>
      
      <div class="context-card">
        <div class="card-header-row">
          <div class="card-title">活跃剧情弧</div>
          <button type="button" class="inline-link" @click="$emit('trigger', buildStructureAction())">
            打开结构页
          </button>
        </div>
        <div v-if="activeArcs.length" class="arc-list">
          <button
            v-for="arc in activeArcs.slice(0, 4)"
            :key="arc.arc_id"
            type="button"
            class="arc-item"
            @click="$emit('trigger', buildArcAction(arc))"
          >
            <div class="arc-title">{{ arc.title || arc.arc_id }}</div>
            <div class="arc-meta">{{ arc.stage || arc.current_stage || '未标注阶段' }} · {{ arc.priority || '未标注优先级' }}</div>
            <div class="arc-cta">查看该剧情弧</div>
          </button>
        </div>
        <p v-else class="card-text empty-text">当前章节还没有可用的活跃剧情弧。</p>
      </div>
      
      <div class="context-card">
        <div class="card-title">最近引用设定</div>
        <p class="card-text">{{ memorySummaryText }}</p>
      </div>
    </div>

    <!-- Inspire Tab -->
    <div v-else class="panel-section inspire-section">
      <div class="inspire-placeholder">
        <p class="sub-text">这里将主动展示为你生成的：</p>
        <ul class="suggestion-list">
          <li>三种可能的剧情分支</li>
          <li>下一章的写作方案</li>
          <li>当前段落的改写方向</li>
        </ul>
      </div>
      
      <div
        v-for="suggestion in suggestedActions"
        :key="suggestion.key"
        class="context-card suggestion-card"
      >
        <div class="card-title">{{ suggestion.title }}</div>
        <p class="card-text">{{ suggestion.description }}</p>
        <el-button type="primary" plain size="small" @click="$emit('trigger', suggestion.action || suggestion.key)">
          {{ suggestion.cta }}
        </el-button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { Cpu, ChatDotRound } from '@element-plus/icons-vue'

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
  chat: '对话',
  context: '上下文',
  inspire: '灵感'
}

const progressText = computed(() => {
  const status = String(props.organizeProgress?.status || '').trim()
  if (!status) return '系统待命中，可随时开始写作。'
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

const memorySummaryText = computed(() => {
  const summary = String(props.memoryView?.current_progress || '').trim()
  if (summary) {
    return summary
  }

  const stageCount = Array.isArray(props.activeArcs) ? props.activeArcs.length : 0
  if (stageCount) {
    return `当前有 ${stageCount} 条可推进剧情弧，可直接进入结构页查看。`
  }

  return '写作过程中提及的人物、世界观与主线约束会逐步汇总在这里。'
})

const buildStructureAction = () => ({
  type: 'section',
  section: 'structure',
  object: {
    type: 'plot_arc'
  }
})

const buildArcAction = (arc) => ({
  type: 'arc',
  arcId: arc?.arc_id || '',
  title: arc?.title || arc?.arc_id || '未命名剧情弧'
})
</script>

<style scoped>
.copilot-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100%;
  width: 320px;
  padding: 20px 16px 16px;
  background-color: #F8FAFC;
  border-left: 1px solid #E5E7EB;
}

.copilot-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-mark {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background-color: #111827;
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-eyebrow {
  margin-bottom: 3px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9CA3AF;
}

.header-icon {
  font-size: 18px;
}

.copilot-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.tab-switcher {
  display: flex;
  background-color: #FFFFFF;
  border-radius: 16px;
  padding: 6px;
  border: 1px solid #E5E7EB;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.03);
}

.tab-button {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 0;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-button.active {
  background-color: #F9FAFB;
  color: #111827;
  box-shadow: inset 0 0 0 1px #E5E7EB;
}

.panel-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  overflow-y: auto;
}

.chat-placeholder, .inspire-placeholder {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px 16px;
  background-color: #FFFFFF;
  border-radius: 18px;
  border: 1px dashed #E5E7EB;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.03);
  color: #4B5563;
  font-size: 13px;
  line-height: 1.6;
}

.placeholder-icon {
  font-size: 24px;
  color: #9CA3AF;
  margin-bottom: 4px;
}

.suggestion-list {
  padding-left: 20px;
  margin: 0;
  color: #6B7280;
}

.suggestion-list li {
  margin-bottom: 6px;
}

.sub-text {
  color: #9CA3AF;
  font-size: 12px;
}

.context-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: 18px;
  background-color: #FFFFFF;
  border: 1px solid #E5E7EB;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.card-text {
  font-size: 13px;
  color: #4B5563;
  line-height: 1.5;
}

.empty-text {
  color: #9CA3AF;
}

.arc-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.arc-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 12px;
  border-radius: 14px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.arc-item:hover {
  border-color: #D1D5DB;
  transform: translateY(-1px);
}

.arc-title {
  font-size: 13px;
  font-weight: 500;
  color: #111827;
}

.arc-meta {
  margin-top: 4px;
  font-size: 11px;
  color: #6B7280;
}

.arc-cta,
.inline-link {
  font-size: 11px;
  font-weight: 600;
  color: #4F46E5;
}

.inline-link {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.suggestion-card {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
}

.suggestion-card .card-title {
  color: #1E40AF;
}

.suggestion-card .card-text {
  color: #1D4ED8;
}
</style>
