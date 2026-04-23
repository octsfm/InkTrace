<template>
  <div class="workspace-writing-studio">
    <header class="writing-header">
      <div class="title-area">
        <div class="title-block">
          <div class="title-label">写作</div>
          <input
            class="chapter-title-input"
            v-model="editorState.chapter.title"
            type="text"
            placeholder="无标题章节"
            @input="workspace.state.markEditorDirty()"
          />
        </div>
        <div class="status-indicator">
          <span v-if="editorState.saving" class="status-saving">正在保存...</span>
          <span v-else-if="editorState.dirty" class="status-dirty">未保存</span>
          <span v-else class="status-saved">已保存</span>
        </div>
      </div>
      <div class="actions-area">
        <div class="action-cluster">
          <el-button text @click="runSingleChapterOrganize" :loading="editorState.aiRunning" :disabled="!editorState.chapter.id">单独整理</el-button>
          <el-button text @click="runAiAction('continue')" :loading="editorState.aiRunning">智能续写</el-button>
          <el-button text @click="runAiAction('generate')" :loading="editorState.aiRunning">按大纲生成</el-button>
          <el-button text @click="runAiAction('optimize')" :loading="editorState.aiRunning">去模板化</el-button>
          <el-button text @click="runAiAction('rewrite')" :loading="editorState.aiRunning">风格改写</el-button>
          <el-button text @click="runAiAction('analyze')" :loading="editorState.aiRunning">智能审查</el-button>
        </div>
        <div class="action-cluster action-cluster-compact">
          <el-button type="primary" :loading="editorState.saving" @click="saveChapter">保存</el-button>
          <el-button @click="toggleZenMode" :type="workspaceStore.isZenMode ? 'primary' : 'default'" plain>
            <el-icon><FullScreen /></el-icon>
          </el-button>
        </div>
      </div>
    </header>

    <WorkspaceActionBar :items="workspaceActionItems" />

    <WorkspaceSummaryChips :items="workspaceSummaryItems" variant="compact" />

    <div class="writing-body">
      <div class="editor-pane">
        <div class="editor-container" v-loading="editorState.loading">
          <el-empty
            v-if="!editorState.chapter.id && !editorState.loading"
            description="请从左侧目录打开一个章节，或创建新章节。"
          />
          <template v-else>
            <div class="editor-context-strip">
              <div class="context-pill">
                <span class="context-pill-label">目标弧</span>
                <span class="context-pill-value">{{ targetArcText }}</span>
              </div>
              <div class="context-pill">
                <span class="context-pill-label">任务状态</span>
                <span class="context-pill-value">{{ currentTaskText }}</span>
              </div>
              <div class="context-pill">
                <span class="context-pill-label">问题单</span>
                <span class="context-pill-value">{{ issueCount }}</span>
              </div>
            </div>
            <div v-if="writingObjectActions.length" class="editor-action-strip">
              <button
                v-for="item in writingObjectActions"
                :key="item.label"
                type="button"
                class="editor-action-button"
                @click="handleWritingAction(item.action)"
              >
                {{ item.label }}
              </button>
            </div>
            <div v-if="editorState.aiRunning" class="editor-banner banner-running">
              正在执行 {{ currentTaskLabel }}，任务完成后会以候选稿、diff 或问题单回流到右侧。
            </div>
            <div v-else-if="hasBlockingIssues" class="editor-banner banner-warning">
              当前有 {{ blockingIssueCount }} 个高优先级问题，保存正文前建议先处理。
            </div>
            <div v-if="resultStatusBanner" class="editor-banner" :class="resultStatusBanner.toneClass">
              <strong>{{ resultStatusBanner.title }}</strong>{{ resultStatusBanner.description ? ` · ${resultStatusBanner.description}` : '' }}
            </div>
            <div v-if="activeIssueTitle" class="editor-banner banner-focus">
              <strong>当前定位问题：</strong>{{ activeIssueTitle }}
              <span v-if="activeIssueDetail"> · {{ activeIssueDetail }}</span>
            </div>
            <div class="editor-shell" :class="{ 'editor-shell-issue-focus': activeIssueIndex >= 0 }">
              <div class="editor-paper">
                <div
                  v-if="inlineResultBlock"
                  class="editor-inline-result-anchor"
                  :class="[`editor-inline-result-anchor-${inlineResultBlock.resultType}`]"
                >
                  <WorkspaceInlineResultBlock
                    :result-type="inlineResultBlock.resultType"
                    :result-label="inlineResultBlock.resultLabel"
                    :title="inlineResultBlock.title"
                    :hint="inlineResultBlock.hint"
                    :description="inlineResultBlock.description"
                    :original-text="inlineResultBlock.originalText"
                    :result-text="inlineResultBlock.resultText"
                    :actions="inlineResultBlock.actions"
                    @action="handleInlineResultAction"
                  />
                </div>
                <bubble-menu
                  v-if="editor && hasSelectionBubble"
                  class="selection-bubble-menu"
                  :editor="editor"
                  plugin-key="writing-selection-bubble"
                  :should-show="shouldShowSelectionBubble"
                >
                  <div class="selection-bubble-content">
                    <div class="selection-bubble-preview">{{ selectedTextPreview }}</div>
                    <div class="selection-bubble-actions">
                      <button type="button" class="selection-bubble-action" @click="sendSelectionToCopilot('explain')">
                        解释片段
                      </button>
                      <button type="button" class="selection-bubble-action" @click="runSelectionAiAction('rewrite')">
                        改写片段
                      </button>
                      <button type="button" class="selection-bubble-action" @click="runSelectionAiAction('analyze')">
                        审查片段
                      </button>
                    </div>
                  </div>
                </bubble-menu>
                <editor-content :editor="editor" class="editor-surface" />
              </div>
            </div>
          </template>
        </div>
      </div>

      <aside v-if="!workspaceStore.isZenMode" ref="inspectorRef" class="writing-inspector">
        <div class="inspector-card">
          <div class="card-header-row">
            <h3>写作状态</h3>
            <el-tag size="small" :type="currentTaskTagType" effect="plain">{{ currentTaskText }}</el-tag>
          </div>
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">章节状态</span>
              <span class="summary-value">{{ chapterStatusText }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">当前字数</span>
              <span class="summary-value">{{ wordCount }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">候选结果</span>
              <span class="summary-value">{{ draftSummaryText }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">审查问题</span>
              <span class="summary-value">{{ issueSummaryText }}</span>
            </div>
            <div class="summary-item summary-item-wide">
              <span class="summary-label">结果状态</span>
              <span class="summary-value">{{ resultBoundaryText }}</span>
            </div>
          </div>
        </div>

        <ChapterTaskCard :task="editorState.chapterTask" />

        <div class="inspector-card">
          <div class="card-header-row">
            <h3>本章剧情弧</h3>
            <span class="card-meta-text">{{ chapterArcCountText }}</span>
          </div>
          <div v-if="chapterArcs.length" class="arc-list">
            <div v-for="arc in chapterArcs" :key="arc.binding_id || arc.arc_id" class="arc-item">
              <div class="arc-item-top">
                <div class="arc-item-title">{{ arc.title || arc.arc_title || arc.arc_id || '未命名剧情弧' }}</div>
                <el-tag size="small" effect="plain">{{ formatBindingRole(arc.binding_role) }}</el-tag>
              </div>
              <div class="arc-item-meta">
                {{ formatArcType(arc.arc_type) }} · {{ formatArcStage(arc.current_stage || arc.stage) }} · {{ formatArcStatus(arc.status) }}
              </div>
            </div>
          </div>
          <div v-else class="empty-copy">当前章节还没有可展示的剧情弧绑定。</div>
        </div>

        <ContextSourcePanel :context="editorState.contextMeta" :task="editorState.chapterTask" />

        <div class="inspector-card">
          <div class="card-header-row">
            <h3>章节细纲</h3>
            <span class="card-meta-text">{{ detailOutlineSceneCountText }}</span>
          </div>
          <div class="detail-outline-actions">
            <el-button size="small" @click="addDetailOutlineScene">新增场景</el-button>
            <el-button size="small" @click="generateDetailOutline" :loading="editorState.aiRunning">AI 生成</el-button>
            <el-button size="small" type="primary" @click="saveDetailOutline" :loading="editorState.saving">保存细纲</el-button>
          </div>
          <div v-if="detailOutlineScenes.length" class="detail-outline-list">
            <div v-for="(scene, idx) in detailOutlineScenes" :key="`scene-${idx}`" class="detail-outline-item">
              <div class="detail-outline-item-header">
                <strong>场景 {{ idx + 1 }}</strong>
                <el-button size="small" text @click="removeDetailOutlineScene(idx)">删除</el-button>
              </div>
              <input v-model="scene.goal" class="detail-input" type="text" placeholder="场景目标" />
              <input v-model="scene.conflict" class="detail-input" type="text" placeholder="场景冲突" />
              <input v-model="scene.turning_point" class="detail-input" type="text" placeholder="转折点" />
              <input v-model="scene.hook" class="detail-input" type="text" placeholder="钩子" />
            </div>
          </div>
          <div v-else class="empty-copy">暂无细纲场景，可手动新增或点击 AI 生成。</div>
        </div>

        <div ref="issuePanelSectionRef">
          <IssuePanelCard
            :issues="issueList"
            :object-actions="issueObjectActions"
            :active-issue-index="focusedIssueIndex"
            @locate="handleLocateIssue"
            @action="handleObjectAction"
            @preview="handlePreviewIssue"
            @preview-leave="handlePreviewLeave"
            @reanalyze="runAiAction('analyze')"
          />
        </div>

        <div ref="draftPreviewSectionRef">
          <DraftPreviewTabs
            title="智能回流区"
            :active-tab="editorState.activeDraftTab"
            :structural-draft="editorState.structuralDraft"
            :detemplated-draft="editorState.detemplatedDraft"
            :integrity-check="editorState.integrityCheck"
            :revision-attempts="editorState.integrityCheck?.revision_attempts || []"
            :used-structural-fallback="Boolean(editorState.detemplatedDraft?.display_fallback_to_structural)"
            @update:active-tab="editorState.activeDraftTab = $event"
            @apply="handleApplyDraft"
            @save-draft="handleSaveDraft"
            @discard="handleDiscardDraft"
          />
        </div>
      </aside>
    </div>

    <footer class="writing-footer">
      <div class="footer-left">
        <span class="word-count">{{ wordCount }} 字</span>
        <span>目标弧：{{ targetArcText }}</span>
        <span>问题单：{{ issueCount }}</span>
      </div>
      <div class="footer-right">
        <span>{{ currentTaskLabel }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Extension, Node } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { ElMessage } from 'element-plus'
import { EditorContent, useEditor, VueNodeViewRenderer } from '@tiptap/vue-3'
import { BubbleMenu } from '@tiptap/vue-3/menus'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { FullScreen } from '@element-plus/icons-vue'
import { chapterEditorApi } from '@/api'

import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar.vue'
import WorkspaceCandidateNodeView from '@/components/workspace/WorkspaceCandidateNodeView.vue'
import WorkspaceInlineResultBlock from '@/components/workspace/WorkspaceInlineResultBlock.vue'
import WorkspaceSummaryChips from '@/components/workspace/WorkspaceSummaryChips.vue'
import DraftPreviewTabs from '@/components/story/DraftPreviewTabs.vue'
import ChapterTaskCard from '@/components/story/ChapterTaskCard.vue'
import ContextSourcePanel from '@/components/story/ContextSourcePanel.vue'
import IssuePanelCard from '@/components/story/IssuePanelCard.vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { ARC_STAGE_LABELS, ARC_STATUS_LABELS, ARC_TYPE_LABELS } from '@/constants/storyLabels'
import { useWorkspaceStore } from '@/stores/workspace'
import { buildWorkspaceResultLabel } from './workspaceTaskModel'

const issueHighlightPluginKey = new PluginKey('issueHighlight')

const IssueHighlightExtension = Extension.create({
  name: 'issueHighlight',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: issueHighlightPluginKey,
        state: {
          init() {
            return DecorationSet.empty
          },
          apply(transaction, decorationSet) {
            const meta = transaction.getMeta(issueHighlightPluginKey)

            if (meta?.clear) {
              return DecorationSet.empty
            }

            if (meta?.from && meta?.to && meta.to > meta.from) {
              return DecorationSet.create(transaction.doc, [
                Decoration.inline(meta.from, meta.to, {
                  class: 'issue-highlight-inline'
                })
              ])
            }

            return decorationSet.map(transaction.mapping, transaction.doc)
          }
        },
        props: {
          decorations(state) {
            return issueHighlightPluginKey.getState(state)
          }
        }
      })
    ]
  }
})

const WorkspaceCandidateBlockNode = Node.create({
  name: 'workspaceCandidateBlock',
  group: 'block',
  atom: true,
  selectable: true,

  addOptions() {
    return {
      onAction: () => {}
    }
  },

  addAttributes() {
    return {
      resultLabel: { default: '候选稿' },
      title: { default: '' },
      hint: { default: '' },
      description: { default: '' },
      resultText: { default: '' },
      candidateIndex: { default: 1 },
      candidateTotal: { default: 1 },
      createdAtLabel: { default: '' }
    }
  },

  parseHTML() {
    return [{ tag: 'workspace-candidate-block' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['workspace-candidate-block', HTMLAttributes]
  },

  addNodeView() {
    return VueNodeViewRenderer(WorkspaceCandidateNodeView)
  }
})

const route = useRoute()
const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const editorState = workspace.state.editor
const inspectorRef = ref(null)
const draftPreviewSectionRef = ref(null)
const issuePanelSectionRef = ref(null)
const selectedText = ref('')
const selectedTextRange = ref({ from: 0, to: 0 })
const candidateQueue = ref([])
const activeCandidateId = ref('')

const selectedChapterId = computed(() => String(route.query.chapterId || workspace.currentChapterId.value || ''))
const candidateQueueStorageKey = computed(() => {
  const projectId = String(workspace.state.projectId || '')
  const chapterId = String(selectedChapterId.value || '')
  if (!projectId || !chapterId) return ''
  return `inktrace:workspace:candidate-queue:${projectId}:${chapterId}`
})

const wordCount = computed(() => (editorState.chapter.content || '').replace(/\s+/g, '').length)
const chapterArcs = computed(() => (Array.isArray(editorState.chapterArcs) ? editorState.chapterArcs : []))
const detailOutlineScenes = computed(() => {
  const scenes = editorState.detailOutline?.scenes
  if (!Array.isArray(scenes)) return []
  return scenes
})
const detailOutlineSceneCountText = computed(() => (
  detailOutlineScenes.value.length ? `${detailOutlineScenes.value.length} 个场景` : '未配置'
))
const issueList = computed(() => (Array.isArray(editorState.integrityCheck?.issue_list) ? editorState.integrityCheck.issue_list : []))
const issueCount = computed(() => issueList.value.length)
const blockingIssueCount = computed(() => issueList.value.filter((item) => item?.severity === 'high').length)
const hasBlockingIssues = computed(() => blockingIssueCount.value > 0)
const draftCount = computed(() => [editorState.structuralDraft, editorState.detemplatedDraft].filter(Boolean).length)
const resultState = computed(() => editorState.resultState || {})
const previewIssueIndex = ref(-1)
const activeIssueIndex = computed(() => workspaceStore.currentObject?.type === 'issue' ? Number(workspaceStore.currentObject?.index ?? -1) : -1)
const focusedIssueIndex = computed(() => (previewIssueIndex.value >= 0 ? previewIssueIndex.value : activeIssueIndex.value))
const activeIssue = computed(() => issueList.value[focusedIssueIndex.value] || null)
const activeIssueTitle = computed(() => activeIssue.value?.title || '')
const activeIssueDetail = computed(() => activeIssue.value?.detail || '')
const currentTaskLabel = computed(() => {
  const task = workspaceStore.currentTask
  if (!task?.label) {
    return '待命中'
  }
  const statusMap = {
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return `${task.label}${statusMap[task.status] ? ` · ${statusMap[task.status]}` : ''}`
})
const currentTaskText = computed(() => {
  const task = workspaceStore.currentTask
  if (!task?.status) return '待命中'
  if (task.status === 'running') return '进行中'
  if (task.status === 'completed') return '已完成'
  if (task.status === 'failed') return '失败'
  return task.status
})
const currentTaskTagType = computed(() => {
  const status = workspaceStore.currentTask?.status
  if (status === 'running') return 'primary'
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
})
const chapterStatusText = computed(() => {
  if (editorState.saving) return '保存中'
  if (editorState.dirty) return '未保存'
  return editorState.chapter?.id ? '已保存' : '未载入'
})
const draftSummaryText = computed(() => {
  if (resultState.value.latestResultType === 'issues') {
    return '最近回流为问题结果'
  }
  if (!draftCount.value) return '暂无'
  return `共 ${draftCount.value} 份`
})
const issueSummaryText = computed(() => {
  if (!issueCount.value) return '无'
  if (blockingIssueCount.value) return `${issueCount.value} 个，其中阻断 ${blockingIssueCount.value} 个`
  return `${issueCount.value} 个`
})
const resultBoundaryText = computed(() => {
  const decisionMap = {
    idle: '待命中',
    pending: '待处理',
    applied_append: '已插入正文',
    applied_replace: '已覆盖正文',
    saved: '已写回并保存',
    discarded: '已放弃',
    error: '执行失败'
  }
  const resultLabel = buildWorkspaceResultLabel(resultState.value.latestResultType, {
    noneLabel: '暂无结果',
    rewriteVariant: 'draft'
  })
  const decisionLabel = decisionMap[resultState.value.lastDecision || 'idle'] || '待处理'
  return `${resultLabel} · ${decisionLabel}`
})
const resultStatusBanner = computed(() => {
  const type = resultState.value.latestResultType || 'none'
  const decision = resultState.value.lastDecision || 'idle'
  if (decision === 'error') {
    return {
      title: '最近一次智能结果执行失败',
      description: resultState.value.lastError || '请检查任务状态后重试。',
      toneClass: 'banner-danger'
    }
  }
  if (type === 'issues' && issueCount.value) {
    return {
      title: '最近回流：问题结果',
      description: `当前有 ${issueCount.value} 个问题单，建议先定位再决定是否改写正文。`,
      toneClass: 'banner-warning'
    }
  }
  if ((type === 'candidate' || type === 'diff') && decision === 'pending') {
    return {
      title: `最近回流：${buildWorkspaceResultLabel(type, { noneLabel: '候选稿', rewriteVariant: 'draft' })}`,
      description: '当前结果尚未写回正文，可选择覆盖、追加、保存或放弃。',
      toneClass: 'banner-info'
    }
  }
  if ((type === 'candidate' || type === 'diff') && ['applied_append', 'applied_replace', 'saved', 'discarded'].includes(decision)) {
    return {
      title: `最近结果状态：${resultBoundaryText.value}`,
      description: '结果区与正文状态已同步，可继续写作或再次发起 AI 操作。',
      toneClass: 'banner-success'
    }
  }
  return null
})
const targetArcText = computed(() => {
  const taskArcId = String(editorState.chapterTask?.target_arc_id || '').trim()
  const taskArc = chapterArcs.value.find((item) => item.arc_id === taskArcId)
  if (taskArc) return taskArc.title || taskArc.arc_title || taskArc.arc_id
  const primaryArc = chapterArcs.value.find((item) => String(item.binding_role || '').toLowerCase() === 'primary')
  if (primaryArc) return primaryArc.title || primaryArc.arc_title || primaryArc.arc_id
  return '自动选择'
})
const chapterArcCountText = computed(() => {
  if (!chapterArcs.value.length) return '暂无绑定'
  return `${chapterArcs.value.length} 条`
})
const issueObjectActions = computed(() => {
  const actions = []

  if (editorState.chapter?.id) {
    actions.push({
      label: '章节管理',
      action: {
        type: 'chapter-manager',
        chapterId: editorState.chapter.id,
        title: editorState.chapter.title || ''
      }
    })
  }

  const taskArcId = String(editorState.chapterTask?.target_arc_id || '').trim()
  const targetArc = chapterArcs.value.find((item) => item.arc_id === taskArcId)
    || chapterArcs.value.find((item) => String(item.binding_role || '').toLowerCase() === 'primary')
    || null

  if (targetArc?.arc_id) {
    actions.push({
      label: '查看目标弧',
      action: {
        type: 'arc',
        arcId: targetArc.arc_id,
        title: targetArc.title || targetArc.arc_title || targetArc.arc_id
      }
    })
  }

  if (issueCount.value) {
    actions.push({
      label: '任务页',
      action: {
        type: 'task-filter',
        filter: 'audit'
      }
    })
  }

  return actions
})
const workspaceActionItems = computed(() => ([
  {
    label: '回到概览',
    primary: true,
    onClick: () => workspace.openSection?.('overview')
  },
  {
    label: '查看结构',
    onClick: () => workspace.openSection?.('structure')
  },
  {
    label: '查看章节',
    onClick: () => workspace.openSection?.('chapters')
  },
  {
    label: '打开任务台',
    onClick: () => workspace.openSection?.('tasks')
  }
]))
const workspaceSummaryItems = computed(() => ([
  { label: '章节状态', value: chapterStatusText.value },
  { label: '目标弧', value: targetArcText.value },
  { label: '任务状态', value: currentTaskText.value },
  { label: '问题单', value: issueSummaryText.value }
]))
const writingObjectActions = computed(() => {
  const actions = []

  if (editorState.chapter?.id) {
    actions.push({
      label: '章节管理',
      action: {
        type: 'chapter-manager',
        chapterId: editorState.chapter.id,
        title: editorState.chapter.title || ''
      }
    })
  }

  const taskArcId = String(editorState.chapterTask?.target_arc_id || '').trim()
  const targetArc = chapterArcs.value.find((item) => item.arc_id === taskArcId)
    || chapterArcs.value.find((item) => String(item.binding_role || '').toLowerCase() === 'primary')
    || null

  if (targetArc?.arc_id) {
    actions.push({
      label: '查看目标弧',
      action: {
        type: 'arc',
        arcId: targetArc.arc_id,
        title: targetArc.title || targetArc.arc_title || targetArc.arc_id
      }
    })
  }

  if (issueCount.value) {
    actions.push({
      label: '重新审查',
      action: {
        type: 'reanalyze'
      }
    })
    actions.push({
      label: '任务页',
      action: {
        type: 'task-filter',
        filter: 'audit'
      }
    })
  }

  return actions
})

const candidateNodeBlock = computed(() => {
  const chapterTitle = editorState.chapter?.title || '当前章节'
  const currentContent = String(editorState.chapter?.content || '')
  const currentCandidate = activeCandidate.value
  const queue = Array.isArray(candidateQueue.value) ? candidateQueue.value : []
  if (currentCandidate) {
    const selectionText = String(currentCandidate.selectionText || '').trim()
    const candidateIndex = Math.max(1, queue.findIndex((item) => item.id === currentCandidate.id) + 1)
    return {
      resultType: 'candidate',
      resultLabel: buildWorkspaceResultLabel('candidate'),
      title: `${selectionText ? '选区候选块' : '行内候选块'} · ${chapterTitle}`,
      hint: selectionText
        ? '选区级候选'
        : (currentCandidate.previewMode === 'delta' ? '新增续写段' : '完整候选稿'),
      description: selectionText
        ? '当前候选块围绕选中文本生成，可先判断局部吸收方式，再决定是否写回正文。'
        : currentCandidate.previewMode === 'delta'
          ? '当前候选块展示新增续写段，可直接并入正文，也可继续在右侧结果区做更细操作。'
          : '当前候选块展示完整候选稿，可先在正文区快速判断是否值得采用。',
      originalText: selectionText || currentContent,
      resultText: currentCandidate.resultText || '',
      candidateIndex,
      candidateTotal: queue.length,
      createdAtLabel: currentCandidate.createdAtLabel,
      actions: [
        { key: 'apply-structural-append', label: '采纳并插入', primary: true },
        { key: 'save-structural', label: '保存草稿' },
        { key: 'open-draft-panel', label: '查看右侧结果区' }
      ]
    }
  }

  return null
})

const inlineResultBlock = computed(() => {
  const chapterTitle = editorState.chapter?.title || '当前章节'
  const currentContent = String(editorState.chapter?.content || '')

  if (editorState.detemplatedDraft && resultState.value.latestResultType === 'diff') {
    const selectionText = String(editorState.detemplatedDraft.selection_context?.text || '').trim()
    return {
      resultType: 'diff',
      resultLabel: buildWorkspaceResultLabel('diff', { rewriteVariant: 'draft' }),
      title: `${selectionText ? '选区改写对照' : '行内改写对照'} · ${chapterTitle}`,
      hint: selectionText ? '选区级改写' : '正文区内对照',
      description: selectionText
        ? '这里直接对比当前选区与改写结果，可先判断是否值得吸收，再决定覆盖、保存或跳到右侧结果区。'
        : '这里直接对比当前正文与改写结果，先判断是否值得采纳，再决定覆盖、保存或跳到右侧结果区。',
      originalText: selectionText || currentContent,
      resultText: editorState.detemplatedDraft.full_content || editorState.detemplatedDraft.content || '',
      actions: [
        { key: 'apply-detemplated-replace', label: '覆盖正文', primary: true },
        { key: 'save-detemplated', label: '保存草稿' },
        { key: 'open-draft-panel', label: '查看右侧结果区' }
      ]
    }
  }

  return null
})

const hasSelectionBubble = computed(() => Boolean(selectedText.value) && !editorState.aiRunning)
const selectedTextPreview = computed(() => {
  const text = String(selectedText.value || '').trim()
  if (!text) return ''
  return text.length > 60 ? `${text.slice(0, 60)}...` : text
})

const clearSelectionContext = () => {
  selectedText.value = ''
  selectedTextRange.value = { from: 0, to: 0 }
}

const formatCandidateTime = (value) => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch (error) {
    return ''
  }
}

const buildCandidateEntryFromDraft = (draft = {}, latestTaskId = '') => {
  const resultText = String(draft.content || draft.full_content || '').trim()
  if (!resultText) return null
  const selectionText = String(draft.selection_context?.text || '').trim()
  const sourceKey = String(latestTaskId || '').trim() || String(draft.source_action || '').trim()
  const fingerprint = `${sourceKey}|${resultText}`
  const createdAt = Date.now()
  return {
    id: `${sourceKey || 'candidate'}-${createdAt}-${Math.random().toString(36).slice(2, 7)}`,
    fingerprint,
    resultText,
    selectionText,
    previewMode: String(draft.preview_mode || 'full'),
    title: String(draft.title || ''),
    createdAt,
    createdAtLabel: formatCandidateTime(createdAt),
    draftSnapshot: JSON.parse(JSON.stringify(draft || {}))
  }
}

const upsertCandidateQueue = () => {
  const draft = editorState.structuralDraft
  if (!draft || resultState.value.latestResultType !== 'candidate') return

  const nextEntry = buildCandidateEntryFromDraft(draft, resultState.value.latestTaskId)
  if (!nextEntry) return

  const queue = Array.isArray(candidateQueue.value) ? [...candidateQueue.value] : []
  if (queue.some((item) => item.fingerprint === nextEntry.fingerprint)) {
    return
  }

  queue.unshift(nextEntry)
  candidateQueue.value = queue.slice(0, 6)
  activeCandidateId.value = nextEntry.id
}

const activeCandidate = computed(() => {
  const queue = Array.isArray(candidateQueue.value) ? candidateQueue.value : []
  if (!queue.length) return null
  const matched = queue.find((item) => item.id === activeCandidateId.value)
  return matched || queue[0]
})

const shiftCandidateCursor = (direction = 1) => {
  const queue = Array.isArray(candidateQueue.value) ? candidateQueue.value : []
  if (!queue.length) return
  const currentIndex = Math.max(0, queue.findIndex((item) => item.id === activeCandidateId.value))
  const nextIndex = (currentIndex + direction + queue.length) % queue.length
  activeCandidateId.value = queue[nextIndex]?.id || queue[0]?.id || ''
}

const dismissCurrentCandidate = () => {
  const queue = Array.isArray(candidateQueue.value) ? [...candidateQueue.value] : []
  if (!queue.length) return false
  const currentIndex = Math.max(0, queue.findIndex((item) => item.id === activeCandidateId.value))
  queue.splice(currentIndex, 1)
  candidateQueue.value = queue
  activeCandidateId.value = queue[Math.min(currentIndex, queue.length - 1)]?.id || ''
  return true
}

const withActiveCandidateDraft = async (runner) => {
  const candidate = activeCandidate.value
  if (!candidate?.draftSnapshot) return false
  const previousDraft = editorState.structuralDraft
  editorState.structuralDraft = JSON.parse(JSON.stringify(candidate.draftSnapshot))
  try {
    await runner()
    return true
  } finally {
    if (editorState.structuralDraft?.content === candidate.draftSnapshot.content) {
      editorState.structuralDraft = previousDraft
    }
  }
}

const persistCandidateQueue = () => {
  const storageKey = candidateQueueStorageKey.value
  if (!storageKey) return
  try {
    const payload = {
      queue: candidateQueue.value || [],
      activeCandidateId: activeCandidateId.value || ''
    }
    localStorage.setItem(storageKey, JSON.stringify(payload))
  } catch (error) {
    // ignore storage errors
  }
}

const loadCandidateQueue = () => {
  const storageKey = candidateQueueStorageKey.value
  if (!storageKey) {
    candidateQueue.value = []
    activeCandidateId.value = ''
    return
  }

  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) {
      candidateQueue.value = []
      activeCandidateId.value = ''
      return
    }
    const parsed = JSON.parse(raw)
    const queue = Array.isArray(parsed?.queue) ? parsed.queue : []
    candidateQueue.value = queue.slice(0, 6)
    activeCandidateId.value = String(parsed?.activeCandidateId || queue[0]?.id || '')
  } catch (error) {
    candidateQueue.value = []
    activeCandidateId.value = ''
  }
}

const adoptCandidateSegment = (segmentText = '') => {
  const text = String(segmentText || '').trim()
  if (!text || !editor.value) return false

  const from = Number(selectedTextRange.value.from || 0)
  const to = Number(selectedTextRange.value.to || 0)
  editor.value.commands.focus()
  if (from > 0 && to > from) {
    editor.value.commands.insertContentAt({ from, to }, text)
  } else {
    editor.value.commands.insertContentAt(editor.value.state.doc.content.size, `\n${text}`)
  }
  workspace.state.markEditorDirty?.()
  clearSelectionContext()
  ElMessage.success('已局部采纳候选片段')
  return true
}

const syncSelectionContext = (nextEditor) => {
  const selection = nextEditor?.state?.selection
  const textBetween = nextEditor?.state?.doc?.textBetween
  if (!selection || typeof textBetween !== 'function' || selection.empty) {
    clearSelectionContext()
    return
  }

  const from = Number(selection.from || 0)
  const to = Number(selection.to || 0)
  if (!from || !to || to <= from) {
    clearSelectionContext()
    return
  }

  const nextSelectedText = normalizeEditorText(textBetween(from, to, '\n', '\n')).trim()
  if (!nextSelectedText) {
    clearSelectionContext()
    return
  }

  selectedText.value = nextSelectedText
  selectedTextRange.value = { from, to }
}

const shouldShowSelectionBubble = ({ editor: nextEditor, state }) => {
  if (editorState.aiRunning) return false
  if (!state?.selection || state.selection.empty) return false
  const selected = normalizeEditorText(nextEditor?.state?.doc?.textBetween?.(state.selection.from, state.selection.to, '\n', '\n') || '').trim()
  return Boolean(selected)
}

const buildSelectionPrompt = (mode) => {
  const chapterTitle = editorState.chapter?.title || '当前章节'
  const selectionBlock = `选中文本：\n「${selectedText.value}」`

  if (mode === 'rewrite') {
    return `请作为小说写作助手，围绕章节《${chapterTitle}》中的这段正文给出 2 个更自然的改写方案，并说明各自适合保留的语气与信息重点。\n\n${selectionBlock}`
  }

  if (mode === 'audit') {
    return `请作为审查助手，检查章节《${chapterTitle}》中的这段正文是否存在一致性、节奏、信息落点或人物状态问题，并按优先级给出修复建议。\n\n${selectionBlock}`
  }

  return `请解释章节《${chapterTitle}》中的这段正文当前承担的剧情、情绪和信息功能，并指出如果继续往下写，最自然的承接方向是什么。\n\n${selectionBlock}`
}

const buildSelectionContext = () => ({
  text: selectedText.value,
  range: {
    from: selectedTextRange.value.from || 0,
    to: selectedTextRange.value.to || 0
  }
})

const sendSelectionToCopilot = (mode) => {
  if (!selectedText.value) {
    ElMessage.info('请先选中一段正文')
    return
  }

  workspaceStore.toggleCopilot(true)
  workspaceStore.setCopilotTab('chat')
  workspaceStore.setCopilotChatDraft(buildSelectionPrompt(mode))
  ElMessage.success('已将选中文本送入 Copilot')
}

const runSelectionAiAction = async (action) => {
  if (!selectedText.value) {
    ElMessage.info('请先选中一段正文')
    return
  }

  await runAiAction(action, {
    contentOverride: selectedText.value,
    selectionContext: buildSelectionContext()
  })
}

const editor = useEditor({
  extensions: [
    StarterKit,
    IssueHighlightExtension,
    WorkspaceCandidateBlockNode.configure({
      onAction: (key, payload) => {
        void handleInlineResultAction(key, payload)
      }
    }),
    Placeholder.configure({
      placeholder: '按 "/" 呼出智能命令，或直接开始写作...'
    })
  ],
  content: '',
  editorProps: {
    attributes: {
      class: 'tiptap-editor'
    }
  },
  onUpdate: ({ editor: nextEditor }) => {
    const nextContent = normalizeEditorText(nextEditor.getText({ blockSeparator: '\n' }))
    if (nextContent !== editorState.chapter.content) {
      editorState.chapter.content = nextContent
      workspace.state.markEditorDirty()
    }
  },
  onSelectionUpdate: ({ editor: nextEditor }) => {
    syncSelectionContext(nextEditor)
  }
})

const findCandidateNodeRange = (nextEditor) => {
  const matches = []
  nextEditor?.state?.doc?.descendants?.((node, pos) => {
    if (node?.type?.name === 'workspaceCandidateBlock') {
      matches.push({ from: pos, to: pos + node.nodeSize })
    }
  })
  return matches
}

const syncCandidateNodeInEditor = () => {
  const nextEditor = editor.value
  if (!nextEditor) return

  const existingRanges = findCandidateNodeRange(nextEditor)
  for (let index = existingRanges.length - 1; index >= 0; index -= 1) {
    nextEditor.commands.deleteRange(existingRanges[index])
  }

  if (!candidateNodeBlock.value) {
    return
  }

  nextEditor.commands.insertContentAt(nextEditor.state.doc.content.size, {
    type: 'workspaceCandidateBlock',
    attrs: {
      resultLabel: candidateNodeBlock.value.resultLabel,
      title: candidateNodeBlock.value.title,
      hint: candidateNodeBlock.value.hint,
      description: candidateNodeBlock.value.description,
      resultText: candidateNodeBlock.value.resultText,
      candidateIndex: candidateNodeBlock.value.candidateIndex,
      candidateTotal: candidateNodeBlock.value.candidateTotal,
      createdAtLabel: candidateNodeBlock.value.createdAtLabel
    }
  })
}

const syncEditorFromStore = (content = '') => {
  if (!editor.value) return
  const currentContent = normalizeEditorText(editor.value.getText({ blockSeparator: '\n' }))
  const nextContent = normalizeEditorText(content)
  if (currentContent === nextContent) return

  editor.value.commands.setContent(plainTextToHtml(nextContent), false)
  clearSelectionContext()
  nextTick(() => {
    syncCandidateNodeInEditor()
  })
}

const saveChapter = async () => {
  await workspace.saveEditorChapter()
  ElMessage.success('章节已保存')
}

const runSingleChapterOrganize = async () => {
  if (!editorState.chapter.id) {
    ElMessage.info('请先选择一个章节')
    return
  }
  await workspace.organizeSingleChapter(editorState.chapter.id, {
    rebuildMemory: true,
    refreshRange: 'self'
  })
  ElMessage.success('单章整理完成')
}

const addDetailOutlineScene = () => {
  const scenes = Array.isArray(editorState.detailOutline?.scenes)
    ? [...editorState.detailOutline.scenes]
    : []
  scenes.push({
    scene_no: scenes.length + 1,
    goal: '',
    conflict: '',
    turning_point: '',
    hook: '',
    foreshadow: '',
    target_words: 1200
  })
  editorState.detailOutline = {
    ...(editorState.detailOutline || {}),
    scenes
  }
}

const removeDetailOutlineScene = (index) => {
  const scenes = Array.isArray(editorState.detailOutline?.scenes)
    ? [...editorState.detailOutline.scenes]
    : []
  if (index < 0 || index >= scenes.length) return
  scenes.splice(index, 1)
  editorState.detailOutline = {
    ...(editorState.detailOutline || {}),
    scenes: scenes.map((item, idx) => ({ ...item, scene_no: idx + 1 }))
  }
}

const saveDetailOutline = async () => {
  if (!editorState.chapter.id) return
  const payload = {
    scenes: (editorState.detailOutline?.scenes || []).map((item, idx) => ({
      scene_no: idx + 1,
      goal: String(item.goal || ''),
      conflict: String(item.conflict || ''),
      turning_point: String(item.turning_point || ''),
      hook: String(item.hook || ''),
      foreshadow: String(item.foreshadow || ''),
      target_words: Number(item.target_words || 0)
    })),
    notes: String(editorState.detailOutline?.notes || '')
  }
  const saved = await chapterEditorApi.saveDetailOutline(editorState.chapter.id, payload)
  editorState.detailOutline = saved || { scenes: [], notes: '' }
  ElMessage.success('章节细纲已保存')
}

const generateDetailOutline = async () => {
  if (!editorState.chapter.id) return
  const generated = await chapterEditorApi.generateDetailOutline(editorState.chapter.id, { source: 'chapter_content' })
  editorState.detailOutline = {
    ...(editorState.detailOutline || {}),
    scenes: Array.isArray(generated?.scenes) ? generated.scenes : []
  }
  ElMessage.success('已生成章节细纲草案')
}

const runAiAction = async (action, options = {}) => {
  await workspace.runEditorAiAction(action, options)
  await revealAiResult(action)
  const messageMap = {
    continue: '智能续写结果已回流到右侧候选区',
    generate: '生成结果已回流到右侧候选区',
    optimize: '去模板化结果已回流到右侧候选区',
    rewrite: '改写结果已回流到右侧候选区',
    analyze: '审查结果已回流到右侧问题区'
  }
  if (options.selectionContext?.text) {
    const selectionMessageMap = {
      rewrite: '选区改写结果已回流到正文区与结果区',
      analyze: '选区审查结果已回流到问题区'
    }
    ElMessage.success(selectionMessageMap[action] || '选区智能结果已提交')
    return
  }
  ElMessage.success(messageMap[action] || '智能任务已提交')
}

const scrollInspectorTo = async (targetRef) => {
  if (workspaceStore.isZenMode) {
    workspaceStore.toggleZenMode(false)
  }
  await nextTick()
  const target = targetRef?.value
  if (target?.scrollIntoView) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  inspectorRef.value?.scrollTo?.({ top: 0, behavior: 'smooth' })
}

const revealAiResult = async (action) => {
  if (action === 'analyze') {
    await scrollInspectorTo(issuePanelSectionRef)
    return
  }

  if (['continue', 'generate', 'optimize', 'rewrite'].includes(action)) {
    await scrollInspectorTo(draftPreviewSectionRef)
  }
}

const toggleZenMode = () => {
  workspaceStore.toggleZenMode()
}

const handleApplyDraft = ({ type, mode }) => {
  const applied = workspace.applyDraftToEditor({ type, mode })
  if (applied) {
    ElMessage.success(mode === 'append' ? '已插入正文末尾' : '已覆盖到当前正文')
    syncEditorFromStore(editorState.chapter.content)
  }
}

const handleSaveDraft = async ({ type }) => {
  const saved = await workspace.saveDraftResult({ type })
  if (saved) {
    syncEditorFromStore(editorState.chapter.content)
    ElMessage.success('草稿已写回并保存')
  }
}

const handleDiscardDraft = ({ type }) => {
  workspace.discardDraft({ type })
  ElMessage.success('已放弃当前候选稿')
}

const buildIssueSearchTerms = (issue) => {
  const rawTerms = [
    issue?.anchor,
    issue?.anchor_text,
    issue?.selected_text,
    issue?.excerpt,
    issue?.quote,
    issue?.focus_text,
    issue?.title
  ]

  return rawTerms
    .map((item) => String(item || '').trim())
    .filter((item) => item && item.length >= 2)
}

const resolveIssueExplicitRange = (issue) => {
  const directFrom = Number(issue?.from ?? issue?.start_offset ?? issue?.start)
  const directTo = Number(issue?.to ?? issue?.end_offset ?? issue?.end)
  if (Number.isFinite(directFrom) && Number.isFinite(directTo) && directTo > directFrom) {
    return { from: directFrom, to: directTo }
  }

  const range = issue?.anchor_range || issue?.range || null
  const rangeFrom = Number(range?.from ?? range?.start)
  const rangeTo = Number(range?.to ?? range?.end)
  if (Number.isFinite(rangeFrom) && Number.isFinite(rangeTo) && rangeTo > rangeFrom) {
    return { from: rangeFrom, to: rangeTo }
  }

  return null
}

const findIssueSelection = (searchTerms) => {
  if (!editor.value?.state?.doc || !Array.isArray(searchTerms) || !searchTerms.length) {
    return null
  }

  let located = null
  editor.value.state.doc.descendants((node, pos) => {
    if (located || !node?.isText) {
      return
    }

    const text = String(node.text || '')
    if (!text) {
      return
    }

    for (const term of searchTerms) {
      const index = text.indexOf(term)
      if (index >= 0) {
        const from = pos + index + 1
        located = {
          from,
          to: from + term.length
        }
        return false
      }
    }
  })

  return located
}

const dispatchIssueHighlight = (payload) => {
  if (!editor.value?.state?.tr?.setMeta || !editor.value?.view?.dispatch) {
    return
  }

  const transaction = editor.value.state.tr.setMeta(issueHighlightPluginKey, payload)
  editor.value.view.dispatch(transaction)
}

const clearIssueHighlight = () => {
  dispatchIssueHighlight({ clear: true })
}

const applyIssueHighlight = (selection) => {
  if (!selection?.from || !selection?.to || selection.to <= selection.from) {
    clearIssueHighlight()
    return
  }

  dispatchIssueHighlight({
    from: selection.from,
    to: selection.to
  })
}

const locateIssueSelection = (issue) => {
  const explicitRange = resolveIssueExplicitRange(issue)
  if (explicitRange) {
    return explicitRange
  }
  const searchTerms = buildIssueSearchTerms(issue)
  return findIssueSelection(searchTerms)
}

const syncHighlightForIssue = (issue) => {
  const selection = locateIssueSelection(issue)
  if (selection?.from && selection?.to) {
    applyIssueHighlight(selection)
    return selection
  }

  clearIssueHighlight()
  return null
}

const handleLocateIssue = ({ issue, index }) => {
  previewIssueIndex.value = -1
  workspaceStore.focusIssue({
    index,
    code: issue?.code || '',
    title: issue?.title || '',
    chapterId: editorState.chapter?.id || ''
  }, { openView: false })

  if (!editor.value) {
    ElMessage.warning('编辑器尚未就绪')
    return
  }

  const selection = syncHighlightForIssue(issue)

  if (selection?.from && selection?.to) {
    editor.value.commands.focus()
    editor.value.commands.setTextSelection(selection)
    ElMessage.success('已定位到正文中的相关片段')
    return
  }

  editor.value.commands.focus('start')
  ElMessage.info('当前问题暂无精确锚点，已聚焦正文，请结合问题说明手动修订')
}

const handlePreviewIssue = ({ issue, index }) => {
  previewIssueIndex.value = index
  syncHighlightForIssue(issue)
}

const handlePreviewLeave = () => {
  previewIssueIndex.value = -1

  if (activeIssueIndex.value < 0) {
    clearIssueHighlight()
    return
  }

  const persistentIssue = issueList.value[activeIssueIndex.value] || null
  if (!persistentIssue) {
    clearIssueHighlight()
    return
  }

  syncHighlightForIssue(persistentIssue)
}

const handleObjectAction = async (payload) => {
  if (!payload || typeof payload !== 'object') {
    return
  }

  if (payload.type === 'chapter-manager' && payload.chapterId) {
    workspaceStore.focusChapterObject({
      id: payload.chapterId,
      title: payload.title || editorState.chapter.title || ''
    }, { openView: true, view: 'chapters' })
    workspace.openSection?.('chapters')
    return
  }

  if (payload.type === 'arc') {
    workspaceStore.focusPlotArc({
      arcId: payload.arcId || '',
      title: payload.title || ''
    }, { openView: true, section: 'plot_arc' })
    workspace.openSection?.('structure')
    return
  }

  if (payload.type === 'task-filter') {
    workspaceStore.focusTaskFilter(payload.filter || 'all', { openView: true })
    workspace.openSection?.('tasks')
    return
  }

  if (payload.type === 'reanalyze') {
    await runAiAction('analyze')
  }
}

const handleWritingAction = async (payload) => {
  await handleObjectAction(payload)
}

const handleInlineResultAction = async (key, payload = {}) => {
  if (key === 'candidate-prev') {
    shiftCandidateCursor(-1)
    return
  }
  if (key === 'candidate-next') {
    shiftCandidateCursor(1)
    return
  }
  if (key === 'candidate-dismiss') {
    if (dismissCurrentCandidate()) {
      ElMessage.info('已忽略当前候选')
    }
    return
  }
  if (key === 'candidate-adopt-segment') {
    adoptCandidateSegment(payload.segmentText || '')
    return
  }
  if (key === 'apply-structural-append') {
    const applied = await withActiveCandidateDraft(async () => {
      handleApplyDraft({ type: 'structural', mode: 'append' })
    })
    if (applied) {
      dismissCurrentCandidate()
    }
    return
  }
  if (key === 'apply-detemplated-replace') {
    handleApplyDraft({ type: 'detemplated', mode: 'replace' })
    return
  }
  if (key === 'save-structural') {
    await withActiveCandidateDraft(async () => {
      await handleSaveDraft({ type: 'structural' })
    })
    return
  }
  if (key === 'save-detemplated') {
    await handleSaveDraft({ type: 'detemplated' })
    return
  }
  if (key === 'open-draft-panel') {
    await withActiveCandidateDraft(async () => {})
    await scrollInspectorTo(draftPreviewSectionRef)
  }
}

const revealFocusedWorkspaceResult = async () => {
  const object = workspaceStore.currentObject
  if (object?.type !== 'writing-result') {
    return
  }

  if (String(object.chapterId || '') && String(object.chapterId || '') !== String(editorState.chapter?.id || '')) {
    return
  }

  if (object.resultType === 'issues') {
    await scrollInspectorTo(issuePanelSectionRef)
    return
  }

  if (object.resultType === 'diff') {
    editorState.activeDraftTab = editorState.detemplatedDraft ? 'detemplated' : editorState.activeDraftTab
    await scrollInspectorTo(draftPreviewSectionRef)
    return
  }

  if (object.resultType === 'candidate') {
    editorState.activeDraftTab = editorState.structuralDraft
      ? 'structural'
      : (editorState.detemplatedDraft ? 'detemplated' : editorState.activeDraftTab)
    await scrollInspectorTo(draftPreviewSectionRef)
  }
}

// Helpers
const escapeHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;')

const plainTextToHtml = (value) => {
  const lines = String(value || '').split(/\r?\n/)
  if (!lines.length) return '<p></p>'
  return lines.map((line) => `<p>${line ? escapeHtml(line) : '<br>'}</p>`).join('')
}

const normalizeEditorText = (value) => String(value || '').replace(/\u00a0/g, ' ').trimEnd()
const formatArcType = (value) => ARC_TYPE_LABELS[value] || value || '未标注类型'
const formatArcStage = (value) => ARC_STAGE_LABELS[value] || value || '未标注阶段'
const formatArcStatus = (value) => ARC_STATUS_LABELS[value] || value || '未标注状态'
const formatBindingRole = (value) => ({
  primary: '主推进',
  secondary: '次推进',
  background: '背景提醒'
}[String(value || '').toLowerCase()] || '未标注')

// Watchers
watch(
  () => [selectedChapterId.value, workspace.state.projectId],
  ([chapterId]) => {
    loadCandidateQueue()
    clearIssueHighlight()
    clearSelectionContext()
    void workspace.loadEditorChapter(chapterId)
  },
  { immediate: true }
)

watch(
  () => [
    workspaceStore.currentObject?.type,
    workspaceStore.currentObject?.chapterId,
    workspaceStore.currentObject?.resultType,
    editorState.chapter?.id
  ],
  () => {
    void revealFocusedWorkspaceResult()
  },
  { immediate: true }
)

watch(
  () => [candidateQueue.value, activeCandidateId.value, candidateQueueStorageKey.value],
  () => {
    persistCandidateQueue()
  },
  { deep: true }
)

watch(
  () => activeIssueIndex.value,
  (index) => {
    if (index < 0) {
      clearIssueHighlight()
      return
    }

    if (previewIssueIndex.value >= 0) {
      return
    }

    const persistentIssue = issueList.value[index] || null
    if (persistentIssue) {
      syncHighlightForIssue(persistentIssue)
    }
  }
)

watch(
  () => [editor.value, editorState.chapter.id, editorState.chapter.content],
  ([nextEditor, , content]) => {
    if (!nextEditor) return
    syncEditorFromStore(content)
  },
  { immediate: true }
)

watch(
  () => [
    editorState.structuralDraft?.content,
    editorState.structuralDraft?.full_content,
    editorState.structuralDraft?.preview_mode,
    resultState.value.latestResultType,
    resultState.value.latestTaskId,
    editorState.chapter?.id
  ],
  () => {
    upsertCandidateQueue()
  },
  { immediate: true }
)

watch(
  () => [
    candidateNodeBlock.value?.title,
    candidateNodeBlock.value?.hint,
    candidateNodeBlock.value?.description,
    candidateNodeBlock.value?.resultText,
    resultState.value.latestResultType,
    editorState.chapter?.id
  ],
  () => {
    nextTick(() => {
      syncCandidateNodeInEditor()
    })
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style scoped>
.workspace-writing-studio {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #F8FAFC;
  min-height: 0;
}

.writing-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 22px 32px 18px;
  border-bottom: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.title-area {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.title-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.title-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6B7280;
}

.chapter-title-input {
  font-size: 30px;
  font-weight: 600;
  color: #111827;
  border: none;
  outline: none;
  background: transparent;
  width: 100%;
  min-width: 240px;
}

.chapter-title-input::placeholder {
  color: #9CA3AF;
}

.status-indicator {
  font-size: 12px;
  flex-shrink: 0;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
}

.status-saving { color: #3B82F6; }
.status-dirty { color: #F59E0B; }
.status-saved { color: #10B981; }

.actions-area {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
}

.action-cluster {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  padding: 6px;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  background-color: #FFFFFF;
}

.action-cluster-compact {
  flex-wrap: nowrap;
}

.workspace-writing-studio :deep(.workspace-action-row) {
  padding: 14px 32px 0;
}

.workspace-writing-studio :deep(.workspace-summary-row) {
  padding: 10px 32px 0;
}

.writing-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.editor-pane {
  flex: 1;
  min-width: 0;
  display: flex;
}

.editor-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.editor-context-strip {
  width: 100%;
  max-width: 920px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.editor-action-strip {
  width: 100%;
  max-width: 920px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.editor-action-button {
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  color: #374151;
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.editor-action-button:hover {
  background-color: #F9FAFB;
  border-color: #D1D5DB;
  transform: translateY(-1px);
}

.context-pill {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
}

.context-pill-label {
  font-size: 11px;
  color: #9CA3AF;
}

.context-pill-value {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.editor-surface {
  width: 100%;
  max-width: 760px;
  min-height: 100%;
}

.editor-banner {
  width: 100%;
  max-width: 920px;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.6;
}

.banner-running {
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  color: #1D4ED8;
}

.banner-warning {
  background-color: #FFFBEB;
  border: 1px solid #FDE68A;
  color: #B45309;
}

.banner-focus {
  background-color: #F5F3FF;
  border: 1px solid #DDD6FE;
  color: #6D28D9;
}

.banner-info {
  background-color: #EFF6FF;
  border: 1px solid #BFDBFE;
  color: #1D4ED8;
}

.banner-success {
  background-color: #F0FDF4;
  border: 1px solid #BBF7D0;
  color: #15803D;
}

.banner-danger {
  background-color: #FEF2F2;
  border: 1px solid #FECACA;
  color: #B91C1C;
}

.editor-shell {
  width: 100%;
  max-width: 920px;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.06);
}

.editor-shell-issue-focus {
  border-color: #C4B5FD;
  box-shadow: 0 18px 40px rgba(124, 58, 237, 0.10);
}

.editor-paper {
  min-height: 100%;
  padding: 40px 56px;
  border-radius: 22px;
  background-color: #FFFFFF;
  border: 1px solid #EEF2F7;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  position: relative;
}

.editor-inline-result-anchor {
  width: 100%;
  max-width: 760px;
  margin: 0 auto 22px;
  position: sticky;
  top: 14px;
  z-index: 4;
}

.editor-inline-result-anchor-candidate :deep(.inline-result-block) {
  border-color: #93C5FD;
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.10);
}

.editor-inline-result-anchor-diff :deep(.inline-result-block) {
  border-color: #86EFAC;
  box-shadow: 0 14px 30px rgba(34, 197, 94, 0.10);
}

.selection-bubble-menu {
  display: inline-flex;
  max-width: 320px;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(17, 24, 39, 0.96);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.24);
  color: #F9FAFB;
}

.selection-bubble-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selection-bubble-preview {
  font-size: 12px;
  line-height: 1.6;
  color: rgba(249, 250, 251, 0.88);
}

.selection-bubble-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.selection-bubble-action {
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  color: #FFFFFF;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.selection-bubble-action:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.24);
}

.editor-surface :deep(.tiptap-editor) {
  outline: none;
  font-size: 18px;
  line-height: 1.8;
  color: #374151;
  font-family: "LXGW WenKai", "Noto Serif SC", serif;
}

.editor-surface :deep(.tiptap-editor p) {
  margin-bottom: 1.2em;
}

.editor-surface :deep(.issue-highlight-inline) {
  background: linear-gradient(180deg, rgba(196, 181, 253, 0.18) 0%, rgba(196, 181, 253, 0.52) 100%);
  border-radius: 0.28em;
  box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.16);
}

.editor-surface :deep(.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  height: 0;
  color: #9CA3AF;
  pointer-events: none;
}

.writing-inspector {
  width: 360px;
  flex-shrink: 0;
  padding: 24px 20px 24px 0;
  overflow-y: auto;
  border-left: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background-color: #F8FAFC;
}

.inspector-card {
  padding: 18px;
  border: 1px solid #E5E7EB;
  border-radius: 18px;
  background-color: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.card-header-row h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.card-meta-text {
  font-size: 12px;
  color: #9CA3AF;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 14px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
}

.summary-item-wide {
  grid-column: 1 / -1;
}

.summary-label {
  font-size: 11px;
  color: #9CA3AF;
}

.summary-value {
  font-size: 13px;
  color: #111827;
  font-weight: 600;
}

.arc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.arc-item {
  padding: 14px;
  border-radius: 14px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
}

.arc-item-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.arc-item-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.arc-item-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #6B7280;
  line-height: 1.5;
}

.empty-copy {
  font-size: 13px;
  line-height: 1.6;
  color: #9CA3AF;
}

.detail-outline-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.detail-outline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-outline-item {
  padding: 12px;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  background: #F9FAFB;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-outline-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-input {
  width: 100%;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12px;
  color: #374151;
  background: #FFFFFF;
}

.writing-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 32px;
  border-top: 1px solid #E5E7EB;
  font-size: 13px;
  color: #6B7280;
  background-color: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
}

.footer-left, .footer-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

@media (max-width: 1280px) {
  .writing-body {
    flex-direction: column;
  }

  .writing-inspector {
    width: auto;
    border-left: none;
    border-top: 1px solid #E5E7EB;
    padding: 20px 32px 24px;
  }

  .editor-paper {
    padding: 28px 32px;
  }
}

@media (max-width: 920px) {
  .writing-header {
    flex-direction: column;
    align-items: stretch;
  }

  .title-area {
    align-items: flex-start;
    flex-direction: column;
  }

  .chapter-title-input {
    min-width: 0;
  }

  .actions-area {
    justify-content: flex-start;
  }
}
</style>
