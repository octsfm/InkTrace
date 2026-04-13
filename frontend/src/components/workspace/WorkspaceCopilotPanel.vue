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
      <div class="chat-hero-card">
        <div class="chat-hero-top">
          <div>
            <div class="card-title">围绕当前对象提问</div>
            <p class="card-text">对话会优先参考当前对象、当前状态和结构约束。</p>
          </div>
          <button type="button" class="inline-link" @click="clearChatMessages">清空对话</button>
        </div>

        <div class="chat-object-row">
          <div class="object-chip">
            <span class="chip-label">当前对象</span>
            <span class="chip-value">{{ resolvedCurrentObjectTitle }}</span>
          </div>
          <div class="object-chip">
            <span class="chip-label">当前状态</span>
            <span class="chip-value">{{ resolvedProgressText }}</span>
          </div>
        </div>

        <div class="quick-insert-row">
          <button type="button" class="quick-insert-button" @click="appendToDraft(`当前对象：${resolvedCurrentObjectTitle}`)">
            插入对象
          </button>
          <button type="button" class="quick-insert-button" @click="appendToDraft(`结构约束：${resolvedMainPlotLines[0] || resolvedMemorySummaryText}`)">
            插入约束
          </button>
          <button type="button" class="quick-insert-button" @click="appendToDraft(`当前状态：${resolvedCurrentStateText}`)">
            插入状态
          </button>
        </div>
      </div>

      <div v-if="chatSessions.length" class="chat-suggestion-card">
        <div class="card-title">对象会话</div>
        <div class="session-list">
          <button
            v-for="session in chatSessions"
            :key="session.key"
            type="button"
            class="session-chip"
            :class="{ active: session.key === currentChatSessionKey }"
            @click="emit('chat-session-change', session.key)"
          >
            <span class="session-topline">
              <span class="session-label">{{ session.label }}</span>
              <span v-if="session.key === currentChatSessionKey" class="session-badge">当前</span>
            </span>
            <span v-if="session.summary" class="session-summary">{{ session.summary }}</span>
            <span v-if="session.metaText" class="session-meta">{{ session.metaText }}</span>
          </button>
        </div>
      </div>

      <div class="chat-message-list">
        <article
          v-for="(message, index) in chatMessages"
          :key="`${message.role}-${index}`"
          class="chat-message"
          :class="message.role"
        >
          <div class="message-role">{{ message.role === 'assistant' ? 'Copilot' : '我' }}</div>
          <div class="message-bubble">{{ message.content }}</div>
        </article>
      </div>

      <div class="chat-suggestion-card">
        <div class="card-title">对象级提问</div>
        <div class="object-prompt-list">
          <article
            v-for="item in resolvedObjectPromptCards"
            :key="item.title"
            class="object-prompt-card"
          >
            <div class="object-prompt-top">
            <div class="object-prompt-title">{{ item.title }}</div>
              <span class="object-prompt-tag">{{ item.tag }}</span>
            </div>
            <p class="object-prompt-desc">{{ item.description }}</p>
            <div class="object-prompt-actions">
              <button type="button" class="prompt-action-button" @click="fillPrompt(item.prompt)">
                注入
              </button>
              <button type="button" class="prompt-action-button primary" @click="submitPrompt(item.prompt)">
                立即发送
              </button>
            </div>
          </article>
        </div>
      </div>

      <div class="chat-suggestion-card">
        <div class="card-title">推荐提问</div>
        <div class="prompt-list">
          <button
            v-for="prompt in resolvedChatPrompts"
            :key="prompt"
            type="button"
            class="prompt-chip"
            @click="fillPrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <div v-if="recentPrompts.length" class="chat-suggestion-card">
        <div class="card-title">最近问题</div>
        <div class="prompt-list">
          <button
            v-for="prompt in recentPrompts"
            :key="prompt"
            type="button"
            class="prompt-chip"
            @click="fillPrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <div class="chat-composer">
        <textarea
          :value="chatDraft"
          class="chat-input"
          rows="4"
          placeholder="输入你想询问的内容，例如：下一章最适合推进哪条剧情弧？"
          @input="$emit('update:chatDraft', $event.target.value)"
          @keydown.ctrl.enter.prevent="submitChat"
        />
        <div class="chat-composer-footer">
          <span class="sub-text">
            {{ chatPending ? '正在整理真实上下文并生成回复...' : '`Ctrl+Enter` 发送，会优先引用真实上下文与结构摘要。' }}
          </span>
          <button type="button" class="send-button" :disabled="chatPending" @click="submitChat">
            {{ chatPending ? '发送中' : '发送' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Context Tab -->
    <div v-else-if="modelValue === 'context'" class="panel-section context-section">
      <div class="context-card">
        <div class="card-header-row">
          <div class="card-title">当前对象</div>
          <button
            v-if="resolvedCurrentObjectAction"
            type="button"
            class="inline-link"
            @click="$emit('trigger', resolvedCurrentObjectAction)"
          >
            查看对象
          </button>
        </div>
        <div class="object-summary">
          <div class="object-name">{{ resolvedCurrentObjectTitle }}</div>
          <div class="object-meta">{{ resolvedCurrentObjectMeta }}</div>
        </div>
      </div>

      <div class="context-card">
        <div class="card-title">当前状态</div>
        <p class="card-text">{{ resolvedProgressText }}</p>
      </div>
      
      <div class="context-card">
        <div class="card-header-row">
          <div class="card-title">活跃剧情弧</div>
          <button type="button" class="inline-link" @click="$emit('trigger', resolvedStructureAction)">
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
        <div class="card-header-row">
          <div class="card-title">结构约束</div>
          <button type="button" class="inline-link" @click="$emit('trigger', resolvedStoryModelAction)">
            打开故事模型
          </button>
        </div>
        <div v-if="resolvedMainPlotLines.length" class="memory-list">
          <button
            v-for="(line, index) in resolvedMainPlotLines"
            :key="`${index}-${line}`"
            type="button"
            class="memory-item"
            @click="$emit('trigger', resolvedStoryModelAction)"
          >
            <span class="memory-index">{{ index + 1 }}</span>
            <span class="memory-text">{{ line }}</span>
          </button>
        </div>
        <p v-else class="card-text">{{ resolvedMemorySummaryText }}</p>
      </div>

      <div class="context-card">
        <div class="card-title">上下文摘要</div>
        <p class="card-text">{{ resolvedCurrentStateText }}</p>
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
import { computed, ref } from 'vue'
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
  currentView: {
    type: String,
    default: 'overview'
  },
  currentObject: {
    type: Object,
    default: () => null
  },
  currentChapterTitle: {
    type: String,
    default: ''
  },
  chatDraft: {
    type: String,
    default: ''
  },
  chatMessages: {
    type: Array,
    default: () => []
  },
  chatPending: {
    type: Boolean,
    default: false
  },
  chatSessions: {
    type: Array,
    default: () => []
  },
  currentChatSessionKey: {
    type: String,
    default: ''
  },
  recentPrompts: {
    type: Array,
    default: () => []
  },
  contextSummary: {
    type: Object,
    default: () => ({})
  },
  currentObjectAction: {
    type: Object,
    default: null
  },
  structureAction: {
    type: Object,
    default: null
  },
  storyModelAction: {
    type: Object,
    default: null
  },
  chatPrompts: {
    type: Array,
    default: () => []
  },
  objectPromptCards: {
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

const emit = defineEmits(['update:modelValue', 'trigger', 'update:chatDraft', 'chat-submit', 'clear-chat', 'chat-session-change'])

const tabs = ['chat', 'context', 'inspire']
const tabLabelMap = {
  chat: '对话',
  context: '上下文',
  inspire: '灵感'
}

const resolvedProgressText = computed(() => props.contextSummary?.progressText || progressText.value)
const resolvedMemorySummaryText = computed(() => props.contextSummary?.memorySummaryText || memorySummaryText.value)
const resolvedMainPlotLines = computed(() => (
  Array.isArray(props.contextSummary?.mainPlotLines) && props.contextSummary.mainPlotLines.length
    ? props.contextSummary.mainPlotLines
    : mainPlotLines.value
))
const resolvedCurrentStateText = computed(() => props.contextSummary?.currentStateText || currentStateText.value)
const resolvedCurrentObjectTitle = computed(() => props.contextSummary?.currentObjectTitle || currentObjectTitle.value)
const resolvedCurrentObjectMeta = computed(() => props.contextSummary?.currentObjectMeta || currentObjectMeta.value)
const resolvedCurrentObjectAction = computed(() => props.currentObjectAction || currentObjectAction.value)
const resolvedStructureAction = computed(() => props.structureAction || buildStructureAction())
const resolvedStoryModelAction = computed(() => props.storyModelAction || buildStoryModelAction())
const resolvedChatPrompts = computed(() => (
  Array.isArray(props.chatPrompts) && props.chatPrompts.length ? props.chatPrompts : chatPrompts.value
))
const resolvedObjectPromptCards = computed(() => (
  Array.isArray(props.objectPromptCards) && props.objectPromptCards.length ? props.objectPromptCards : objectPromptCards.value
))

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

const mainPlotLines = computed(() => {
  const lines = Array.isArray(props.memoryView?.main_plot_lines) ? props.memoryView.main_plot_lines : []
  return lines.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
})

const currentStateText = computed(() => {
  const stateText = String(props.memoryView?.current_state || '').trim()
  if (stateText) {
    return stateText
  }
  return '当前对象相关的阶段状态、角色压力和上下文摘要会汇总在这里。'
})

const currentObjectTitle = computed(() => {
  if (props.currentView === 'writing') {
    return props.currentChapterTitle || '当前章节'
  }
  if (props.currentObject?.title) {
    return props.currentObject.title
  }
  if (props.currentObject?.type === 'task-filter') {
    return `任务筛选：${props.currentObject.filter || 'all'}`
  }
  return '当前工作对象'
})

const currentObjectMeta = computed(() => {
  const objectType = String(props.currentObject?.type || '').trim()
  if (props.currentView === 'writing') {
    return '正文写作对象'
  }
  if (props.currentView === 'structure') {
    return objectType === 'plot_arc' ? '剧情弧对象' : '结构对象'
  }
  if (props.currentView === 'chapters') {
    return '章节管理对象'
  }
  if (props.currentView === 'tasks') {
    return objectType === 'task' ? '任务对象' : '任务筛选对象'
  }
  return '当前工作区对象'
})

const currentObjectAction = computed(() => {
  if (props.currentView === 'writing' && props.currentObject?.id) {
    return {
      type: 'chapter-manager',
      chapterId: props.currentObject.id,
      title: props.currentObject.title || props.currentChapterTitle || ''
    }
  }
  if (props.currentView === 'structure' && props.currentObject?.type === 'plot_arc') {
    return {
      type: 'arc',
      arcId: props.currentObject.arcId || '',
      title: props.currentObject.title || ''
    }
  }
  if (props.currentView === 'chapters' && props.currentObject?.type === 'chapter') {
    return {
      type: 'chapter',
      chapterId: props.currentObject.id,
      title: props.currentObject.title || ''
    }
  }
  if (props.currentView === 'tasks' && props.currentObject?.type === 'task-filter') {
    return {
      type: 'task-filter',
      filter: props.currentObject.filter || 'all'
    }
  }
  return null
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

const buildStoryModelAction = () => ({
  type: 'section',
  section: 'structure',
  object: {
    type: 'story_model'
  }
})

const chatPrompts = computed(() => {
  if (props.currentView === 'writing') {
    return [
      '下一章最适合推进哪条剧情弧？',
      '当前章节还有哪些一致性风险？',
      '这章结尾最适合留下什么悬念？'
    ]
  }
  if (props.currentView === 'structure') {
    return [
      '这条剧情弧下一步应该推进到哪个阶段？',
      '当前结构里最大的风险点是什么？',
      '哪些设定还缺少落地章节？'
    ]
  }
  if (props.currentView === 'tasks') {
    return [
      '当前失败任务优先应该恢复哪一个？',
      '这个任务失败最可能是什么原因？',
      '我下一步应该先回到哪个对象处理？'
    ]
  }
  return [
    '我应该从哪里继续创作？',
    '最近最值得关注的对象是什么？',
    '下一步最适合进入哪个工作区？'
  ]
})

const objectPromptCards = computed(() => {
  if (props.currentView === 'writing') {
    return [
      {
        title: '评估当前章节风险',
        tag: '审查',
        description: '快速检查当前章节是否存在一致性、节奏或信息落点问题。',
        prompt: `请检查当前章节「${currentObjectTitle.value}」还有哪些一致性风险，并按优先级给出处理建议。`
      },
      {
        title: '规划下一步剧情弧',
        tag: '结构',
        description: '围绕当前章节和结构约束，决定下一步最该推进的剧情弧。',
        prompt: `围绕当前章节「${currentObjectTitle.value}」，下一步最适合推进哪条剧情弧？请结合当前结构约束给出理由。`
      },
      {
        title: '生成结尾方案',
        tag: '写作',
        description: '给当前章节生成更具悬念感的收束方向。',
        prompt: `请为当前章节「${currentObjectTitle.value}」提供三个结尾悬念方案，并说明各自适合的情绪强度。`
      }
    ]
  }

  if (props.currentView === 'structure') {
    return [
      {
        title: '推进当前结构对象',
        tag: '结构',
        description: '判断当前结构对象下一步应该推进到哪个阶段。',
        prompt: `对于当前结构对象「${currentObjectTitle.value}」，下一步应该推进到哪个阶段？请说明原因。`
      },
      {
        title: '找缺口章节',
        tag: '落地',
        description: '从结构约束反推还缺哪些章节落地。',
        prompt: '根据当前结构约束，哪些设定或剧情弧还缺少对应章节来承接？'
      }
    ]
  }

  if (props.currentView === 'tasks') {
    return [
      {
        title: '恢复失败任务',
        tag: '恢复',
        description: '优先判断当前失败任务是否应该立刻恢复。',
        prompt: `请分析当前任务对象「${currentObjectTitle.value}」，下一步最适合先恢复、重试还是回到对应对象处理？`
      },
      {
        title: '排序处理优先级',
        tag: '任务',
        description: '给出当前任务页的处理顺序建议。',
        prompt: '请根据当前任务状态，给我一个失败任务、审查任务和整理任务的处理优先级。'
      }
    ]
  }

  if (props.currentView === 'chapters') {
    return [
      {
        title: '判断章节功能',
        tag: '章节',
        description: '评估当前章节在全书中的位置是否清晰。',
        prompt: `请评估当前章节「${currentObjectTitle.value}」在整本书中的功能是否清晰，并给出修改建议。`
      },
      {
        title: '安排下一章',
        tag: '规划',
        description: '围绕当前章节推导下一章应该承接什么。',
        prompt: `基于当前章节「${currentObjectTitle.value}」，下一章最应该承接什么信息或冲突？`
      }
    ]
  }

  return [
    {
      title: '决定下一步',
      tag: '概览',
      description: '围绕当前工作区状态决定下一步最合适的入口。',
      prompt: '请根据当前工作区状态，告诉我下一步最适合进入哪个对象继续处理。'
    }
  ]
})

const chatIntroMessage = computed(() => ({
  role: 'assistant',
  content: `我正在关注「${resolvedCurrentObjectTitle.value}」。当前状态是：${resolvedProgressText.value}`
}))

const chatMessages = computed(() => [chatIntroMessage.value, ...(Array.isArray(props.chatMessages) ? props.chatMessages : [])])

const fillPrompt = (prompt) => {
  emit('update:chatDraft', prompt)
}

const submitPrompt = (prompt) => {
  const content = String(prompt || '').trim()
  if (!content) {
    return
  }
  emit('chat-submit', content)
}

const appendToDraft = (segment) => {
  const nextText = [props.chatDraft, segment]
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .join('\n')
  emit('update:chatDraft', nextText)
}

const submitChat = () => {
  const content = String(props.chatDraft || '').trim()
  if (!content) {
    return
  }
  emit('chat-submit', content)
}

const clearChatMessages = () => {
  emit('clear-chat')
}
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

.chat-hero-card,
.chat-suggestion-card,
.inspire-placeholder {
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

.chat-hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.chat-object-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.quick-insert-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-insert-button {
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  color: #374151;
  border-radius: 999px;
  padding: 7px 11px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-insert-button:hover {
  background-color: #FFFFFF;
  border-color: #D1D5DB;
}

.object-chip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.chip-label {
  font-size: 11px;
  color: #9CA3AF;
}

.chip-value {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
  color: #111827;
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

.chat-message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 2px;
}

.chat-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.message-role {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
}

.message-bubble {
  padding: 12px 14px;
  border-radius: 16px;
  line-height: 1.65;
  font-size: 13px;
}

.chat-message.assistant .message-bubble {
  background-color: #FFFFFF;
  border: 1px solid #E5E7EB;
  color: #374151;
}

.chat-message.user {
  align-items: flex-end;
}

.chat-message.user .message-role {
  color: #6B7280;
}

.chat-message.user .message-bubble {
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  color: #1D4ED8;
}

.prompt-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.session-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.session-chip {
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  color: #374151;
  border-radius: 16px;
  padding: 10px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 220px;
}

.session-chip.active {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
  color: #1D4ED8;
  box-shadow: 0 0 0 1px #BFDBFE inset;
}

.session-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.session-label {
  font-size: 12px;
  font-weight: 600;
}

.session-badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  color: #1D4ED8;
  background-color: #DBEAFE;
  border-radius: 999px;
  padding: 2px 7px;
}

.session-summary {
  font-size: 11px;
  line-height: 1.5;
  color: #6B7280;
}

.session-meta {
  font-size: 10px;
  color: #9CA3AF;
}

.object-prompt-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.object-prompt-card {
  padding: 12px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.object-prompt-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.object-prompt-title {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.object-prompt-tag {
  font-size: 11px;
  color: #4F46E5;
  background-color: #EEF2FF;
  border: 1px solid #C7D2FE;
  border-radius: 999px;
  padding: 3px 8px;
}

.object-prompt-desc {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: #6B7280;
}

.object-prompt-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.prompt-action-button {
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  color: #374151;
  border-radius: 10px;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.prompt-action-button.primary {
  background-color: #111827;
  border-color: #111827;
  color: #FFFFFF;
}

.prompt-action-button:hover {
  border-color: #D1D5DB;
}

.prompt-chip {
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  color: #374151;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.prompt-chip:hover {
  background-color: #FFFFFF;
  border-color: #D1D5DB;
}

.chat-composer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.chat-input {
  width: 100%;
  resize: vertical;
  min-height: 96px;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  background-color: #F9FAFB;
  outline: none;
}

.chat-input:focus {
  border-color: #C7D2FE;
  background-color: #FFFFFF;
}

.chat-composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.send-button {
  border: 1px solid #111827;
  background-color: #111827;
  color: #FFFFFF;
  border-radius: 12px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.send-button:hover {
  opacity: 0.92;
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.object-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.object-name {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.object-meta {
  font-size: 12px;
  color: #6B7280;
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

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-item {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 10px;
  align-items: flex-start;
  width: 100%;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.memory-item:hover {
  border-color: #D1D5DB;
  transform: translateY(-1px);
}

.memory-index {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background-color: #E5E7EB;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.memory-text {
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
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
