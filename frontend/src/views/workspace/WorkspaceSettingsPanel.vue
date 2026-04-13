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
              <dt>项目 ID</dt>
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
          <h3>模型与 Copilot</h3>
          <dl class="settings-list">
            <div>
              <dt>Copilot</dt>
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
              <dt>Zen Mode</dt>
              <dd>{{ zenModeText }}</dd>
            </div>
          </dl>
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
  { label: 'Copilot', value: copilotStatusText.value }
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

@media (max-width: 1024px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
