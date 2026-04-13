<template>
  <div class="workspace-page">
    <WorkspacePageHero
      eyebrow="设置"
      title="工作区设置与诊断"
      description="集中查看项目、模型、任务与编辑器状态，确认当前工作区的运行前提是否完整。"
    >
      <WorkspaceHeroChips :items="heroChipItems" />
    </WorkspacePageHero>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <h2>当前配置</h2>
            <p>把项目绑定、模型能力和当前工作区上下文放在同一页，减少来回寻找配置入口。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <WorkspaceSummaryChips :items="summaryItems" />
      <WorkspaceActionBar :items="actionItems" />
      <WorkspaceInfoBanner v-if="bannerText" :text="bannerText" :tone="bannerTone" />

      <div class="settings-grid">
        <article class="settings-card">
          <h3>项目与小说</h3>
          <dl class="settings-list">
            <div>
              <dt>小说标题</dt>
              <dd>{{ novelTitle }}</dd>
            </div>
            <div>
              <dt>项目编号</dt>
              <dd>{{ projectIdText }}</dd>
            </div>
            <div>
              <dt>章节数量</dt>
              <dd>{{ chapterCountText }}</dd>
            </div>
            <div>
              <dt>当前视图</dt>
              <dd>{{ currentViewText }}</dd>
            </div>
          </dl>
        </article>

        <article class="settings-card">
          <h3>模型与助手</h3>
          <dl class="settings-list">
            <div>
              <dt>助手</dt>
              <dd>{{ copilotStatusText }}</dd>
            </div>
            <div>
              <dt>会话上下文</dt>
              <dd>{{ currentContextText }}</dd>
            </div>
            <div>
              <dt>最近提示词</dt>
              <dd>{{ recentPromptText }}</dd>
            </div>
            <div>
              <dt>聊天会话</dt>
              <dd>{{ sessionCountText }}</dd>
            </div>
          </dl>
        </article>

        <article class="settings-card">
          <h3>任务与整理</h3>
          <dl class="settings-list">
            <div>
              <dt>整理状态</dt>
              <dd>{{ taskStatusText }}</dd>
            </div>
            <div>
              <dt>失败任务</dt>
              <dd>{{ failedTaskText }}</dd>
            </div>
            <div>
              <dt>运行中任务</dt>
              <dd>{{ runningTaskText }}</dd>
            </div>
            <div>
              <dt>审查任务</dt>
              <dd>{{ auditTaskText }}</dd>
            </div>
          </dl>
        </article>

        <article class="settings-card">
          <h3>编辑器状态</h3>
          <dl class="settings-list">
            <div>
              <dt>当前章节</dt>
              <dd>{{ currentChapterText }}</dd>
            </div>
            <div>
              <dt>保存状态</dt>
              <dd>{{ saveStatusText }}</dd>
            </div>
            <div>
              <dt>问题单</dt>
              <dd>{{ issueCountText }}</dd>
            </div>
            <div>
              <dt>专注模式</dt>
              <dd>{{ zenModeText }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <h2>工作区诊断</h2>
            <p>把当前最需要处理的阻塞、风险和可继续项集中展示，避免在多个页之间来回判断。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <div class="diagnostic-grid">
        <article
          v-for="item in diagnosticCards"
          :key="item.key"
          class="diagnostic-card"
          :class="item.tone ? `tone-${item.tone}` : ''"
        >
          <div class="diagnostic-top">
            <span class="diagnostic-label">{{ item.label }}</span>
            <span class="diagnostic-state">{{ item.state }}</span>
          </div>
          <div class="diagnostic-title">{{ item.title }}</div>
          <p class="diagnostic-description">{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <h2>建议动作</h2>
            <p>这里不是配置表，而是把最自然的恢复、回写和排查动作直接抬出来。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <div class="decision-grid">
        <article
          v-for="item in decisionCards"
          :key="item.key"
          class="decision-card"
        >
          <div class="decision-top">
            <span class="decision-tag">{{ item.tag }}</span>
            <span class="decision-cta">{{ item.cta }}</span>
          </div>
          <div class="decision-title">{{ item.title }}</div>
          <p class="decision-description">{{ item.description }}</p>
          <div class="decision-meta">{{ item.meta }}</div>
          <el-button size="small" type="primary" plain @click="item.onClick">
            {{ item.cta }}
          </el-button>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar.vue'
import WorkspaceHeroChips from '@/components/workspace/WorkspaceHeroChips.vue'
import WorkspaceInfoBanner from '@/components/workspace/WorkspaceInfoBanner.vue'
import WorkspacePageHero from '@/components/workspace/WorkspacePageHero.vue'
import WorkspaceSectionHeader from '@/components/workspace/WorkspaceSectionHeader.vue'
import WorkspaceSummaryChips from '@/components/workspace/WorkspaceSummaryChips.vue'

const props = defineProps({
  novelTitle: {
    type: String,
    default: ''
  },
  projectId: {
    type: String,
    default: ''
  },
  chapterCount: {
    type: Number,
    default: 0
  },
  currentView: {
    type: String,
    default: 'overview'
  },
  currentChapterTitle: {
    type: String,
    default: ''
  },
  saveStatusText: {
    type: String,
    default: ''
  },
  taskStatusText: {
    type: String,
    default: ''
  },
  failedTaskCount: {
    type: Number,
    default: 0
  },
  runningTaskCount: {
    type: Number,
    default: 0
  },
  auditTaskCount: {
    type: Number,
    default: 0
  },
  issueCount: {
    type: Number,
    default: 0
  },
  copilotOpen: {
    type: Boolean,
    default: false
  },
  recentPromptCount: {
    type: Number,
    default: 0
  },
  sessionCount: {
    type: Number,
    default: 0
  },
  zenMode: {
    type: Boolean,
    default: false
  },
  currentObjectTitle: {
    type: String,
    default: ''
  },
  actionItems: {
    type: Array,
    default: () => []
  }
})

const viewLabelMap = {
  overview: '概览',
  writing: '写作',
  structure: '结构',
  chapters: '章节管理',
  tasks: '任务与审查',
  settings: '设置'
}

const novelTitle = computed(() => props.novelTitle || '未命名小说')
const projectIdText = computed(() => props.projectId || '未绑定项目')
const chapterCountText = computed(() => `${props.chapterCount || 0} 个章节`)
const currentViewText = computed(() => viewLabelMap[props.currentView] || props.currentView || '概览')
const currentChapterText = computed(() => props.currentChapterTitle || '未打开章节')
const copilotStatusText = computed(() => (props.copilotOpen ? '已开启' : '已关闭'))
const currentContextText = computed(() => props.currentObjectTitle || currentViewText.value)
const recentPromptText = computed(() => `${props.recentPromptCount || 0} 条`)
const sessionCountText = computed(() => `${props.sessionCount || 0} 个`)
const failedTaskText = computed(() => `${props.failedTaskCount || 0} 个`)
const runningTaskText = computed(() => `${props.runningTaskCount || 0} 个`)
const auditTaskText = computed(() => `${props.auditTaskCount || 0} 个`)
const issueCountText = computed(() => `${props.issueCount || 0} 个`)
const zenModeText = computed(() => (props.zenMode ? '已开启' : '未开启'))

const heroChipItems = computed(() => ([
  { label: '当前视图', value: currentViewText.value },
  { label: '整理状态', value: props.taskStatusText || '未运行' },
  { label: '助手', value: copilotStatusText.value }
]))

const summaryItems = computed(() => ([
  { label: '失败任务', value: failedTaskText.value, tone: props.failedTaskCount > 0 ? 'danger' : 'default' },
  { label: '运行中任务', value: runningTaskText.value, tone: props.runningTaskCount > 0 ? 'primary' : 'default' },
  { label: '问题单', value: issueCountText.value, tone: props.issueCount > 0 ? 'warning' : 'default' },
  { label: '最近提示词', value: recentPromptText.value }
]))

const bannerText = computed(() => {
  if (!props.projectId) {
    return '当前小说还未绑定项目，结构分析和任务回流能力可能不完整。'
  }
  if (props.failedTaskCount > 0) {
    return `当前有 ${props.failedTaskCount} 个失败任务，建议先恢复失败链路再继续推进。`
  }
  if (props.issueCount > 0) {
    return `当前章节有 ${props.issueCount} 个问题单，适合先回到写作页处理。`
  }
  return '当前工作区状态基本完整，可以继续写作、结构推进或处理任务。'
})

const bannerTone = computed(() => {
  if (!props.projectId || props.failedTaskCount > 0) return 'warning'
  if (props.issueCount > 0) return 'primary'
  return 'success'
})

const diagnosticCards = computed(() => ([
  {
    key: 'binding',
    label: '项目绑定',
    state: props.projectId ? '已连接' : '待确认',
    title: props.projectId ? '项目与工作区已绑定' : '当前还未绑定项目',
    description: props.projectId
      ? `当前项目编号：${props.projectId}`
      : '未绑定时，结构分析、任务恢复和部分上下文回流能力可能不完整。',
    tone: props.projectId ? 'success' : 'warning'
  },
  {
    key: 'tasks',
    label: '任务链路',
    state: props.failedTaskCount > 0 ? '需恢复' : (props.runningTaskCount > 0 ? '运行中' : '稳定'),
    title: props.failedTaskCount > 0 ? `有 ${props.failedTaskCount} 个失败任务待处理` : (props.runningTaskCount > 0 ? '仍有任务在运行' : '当前没有明显任务阻塞'),
    description: props.failedTaskCount > 0
      ? '优先恢复失败任务，能减少后续结构和章节判断被旧结果污染。'
      : (props.runningTaskCount > 0 ? `当前有 ${props.runningTaskCount} 个运行中任务，适合先观察结果回流。`
        : '当前任务状态相对平稳，可以继续写作或回到结构推进。'),
    tone: props.failedTaskCount > 0 ? 'warning' : (props.runningTaskCount > 0 ? 'primary' : 'success')
  },
  {
    key: 'editor',
    label: '正文与问题单',
    state: props.issueCount > 0 ? '待处理' : '正常',
    title: props.issueCount > 0 ? `当前有 ${props.issueCount} 个问题单` : '当前正文没有待处理问题单',
    description: props.issueCount > 0
      ? '建议先回到写作页，处理一致性和结构风险后再继续推进。'
      : `当前章节：${currentChapterText.value}`,
    tone: props.issueCount > 0 ? 'primary' : 'success'
  }
]))

const getActionItem = (key) => props.actionItems.find((item) => item.key === key)

const decisionCards = computed(() => {
  const cards = []

  if (props.failedTaskCount > 0) {
    cards.push({
      key: 'failed-tasks',
      tag: '任务',
      cta: '查看任务',
      title: '先恢复失败任务',
      description: '当前存在失败链路，优先恢复后再继续写作或结构推进会更稳。',
      meta: `${props.failedTaskCount} 个失败任务`,
      onClick: () => getActionItem('settings-open-tasks')?.onClick?.()
    })
  }

  if (props.issueCount > 0) {
    cards.push({
      key: 'issue-loop',
      tag: '写作',
      cta: '回到写作',
      title: '先处理当前问题单',
      description: '当前章节已有问题单，适合先回正文闭环，再继续任务和结构判断。',
      meta: `${props.issueCount} 个问题待处理`,
      onClick: () => getActionItem('settings-open-writing')?.onClick?.()
    })
  }

  cards.push({
    key: 'structure-check',
    tag: '结构',
    cta: '查看结构',
    title: '检查当前结构焦点',
    description: '在继续正文前，先确认当前工作区对象和结构推进方向是否一致。',
    meta: currentContextText.value || '当前工作区对象',
    onClick: () => getActionItem('settings-open-structure')?.onClick?.()
  })

  if (!cards.length) {
    cards.push({
      key: 'continue-writing',
      tag: '写作',
      cta: '回到写作',
      title: '工作区状态稳定，可继续创作',
      description: '当前没有明显失败任务或问题单，适合直接回到正文推进。',
      meta: currentChapterText.value,
      onClick: () => getActionItem('settings-open-writing')?.onClick?.()
    })
  }

  return cards.slice(0, 3)
})
</script>

<style scoped>
.workspace-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.diagnostic-grid,
.decision-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.settings-card {
  padding: 20px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.settings-card h3 {
  margin: 0 0 14px;
  font-size: 16px;
  color: #111827;
}

.settings-list {
  display: grid;
  gap: 12px;
  margin: 0;
}

.settings-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F3F4F6;
}

.settings-list div:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.settings-list dt {
  color: #6B7280;
  font-size: 13px;
}

.settings-list dd {
  margin: 0;
  color: #111827;
  font-size: 13px;
  text-align: right;
}

.diagnostic-card,
.decision-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diagnostic-card.tone-primary {
  border-color: #BFDBFE;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
}

.diagnostic-card.tone-warning {
  border-color: #FDE68A;
  background: linear-gradient(180deg, #FFFFFF 0%, #FFFBEB 100%);
}

.diagnostic-card.tone-success {
  border-color: #BBF7D0;
  background: linear-gradient(180deg, #FFFFFF 0%, #F0FDF4 100%);
}

.diagnostic-top,
.decision-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.diagnostic-label,
.decision-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2563EB;
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  border-radius: 999px;
  padding: 3px 8px;
}

.diagnostic-state,
.decision-cta {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
}

.diagnostic-title,
.decision-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.diagnostic-description,
.decision-description {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.decision-meta {
  font-size: 12px;
  color: #9CA3AF;
}

@media (max-width: 1024px) {
  .settings-grid,
  .diagnostic-grid,
  .decision-grid {
    grid-template-columns: 1fr;
  }
}
</style>
