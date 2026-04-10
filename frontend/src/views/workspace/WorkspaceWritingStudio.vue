<template>
  <div class="workspace-writing-studio">
    <header class="writing-header">
      <div class="title-area">
        <div class="title-block">
          <div class="title-label">Writing</div>
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
          <el-button text @click="runAiAction('continue')" :loading="editorState.aiRunning">AI 续写</el-button>
          <el-button text @click="runAiAction('generate')" :loading="editorState.aiRunning">按大纲生成</el-button>
          <el-button text @click="runAiAction('optimize')" :loading="editorState.aiRunning">去模板化</el-button>
          <el-button text @click="runAiAction('rewrite')" :loading="editorState.aiRunning">风格改写</el-button>
          <el-button text @click="runAiAction('analyze')" :loading="editorState.aiRunning">AI 审查</el-button>
        </div>
        <div class="action-cluster action-cluster-compact">
          <el-button type="primary" :loading="editorState.saving" @click="saveChapter">保存</el-button>
          <el-button @click="toggleZenMode" :type="workspaceStore.isZenMode ? 'primary' : 'default'" plain>
            <el-icon><FullScreen /></el-icon>
          </el-button>
        </div>
      </div>
    </header>

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
            <div v-if="activeIssueTitle" class="editor-banner banner-focus">
              <strong>当前定位问题：</strong>{{ activeIssueTitle }}
              <span v-if="activeIssueDetail"> · {{ activeIssueDetail }}</span>
            </div>
            <div class="editor-shell" :class="{ 'editor-shell-issue-focus': activeIssueIndex >= 0 }">
              <div class="editor-paper">
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
            title="AI 回流区"
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
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { ElMessage } from 'element-plus'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { FullScreen } from '@element-plus/icons-vue'

import DraftPreviewTabs from '@/components/story/DraftPreviewTabs.vue'
import ChapterTaskCard from '@/components/story/ChapterTaskCard.vue'
import ContextSourcePanel from '@/components/story/ContextSourcePanel.vue'
import IssuePanelCard from '@/components/story/IssuePanelCard.vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { ARC_STAGE_LABELS, ARC_STATUS_LABELS, ARC_TYPE_LABELS } from '@/constants/storyLabels'
import { useWorkspaceStore } from '@/stores/workspace'

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

const route = useRoute()
const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const editorState = workspace.state.editor
const inspectorRef = ref(null)
const draftPreviewSectionRef = ref(null)
const issuePanelSectionRef = ref(null)

const selectedChapterId = computed(() => String(route.query.chapterId || workspace.currentChapterId.value || ''))

const wordCount = computed(() => (editorState.chapter.content || '').replace(/\s+/g, '').length)
const chapterArcs = computed(() => (Array.isArray(editorState.chapterArcs) ? editorState.chapterArcs : []))
const issueList = computed(() => (Array.isArray(editorState.integrityCheck?.issue_list) ? editorState.integrityCheck.issue_list : []))
const issueCount = computed(() => issueList.value.length)
const blockingIssueCount = computed(() => issueList.value.filter((item) => item?.severity === 'high').length)
const hasBlockingIssues = computed(() => blockingIssueCount.value > 0)
const draftCount = computed(() => [editorState.structuralDraft, editorState.detemplatedDraft].filter(Boolean).length)
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
  if (!draftCount.value) return '暂无'
  return `共 ${draftCount.value} 份`
})
const issueSummaryText = computed(() => {
  if (!issueCount.value) return '无'
  if (blockingIssueCount.value) return `${issueCount.value} 个，其中阻断 ${blockingIssueCount.value} 个`
  return `${issueCount.value} 个`
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

const editor = useEditor({
  extensions: [
    StarterKit,
    IssueHighlightExtension,
    Placeholder.configure({
      placeholder: '按 "/" 呼出 AI 命令，或直接开始写作...'
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
  }
})

const syncEditorFromStore = (content = '') => {
  if (!editor.value) return
  const currentContent = normalizeEditorText(editor.value.getText({ blockSeparator: '\n' }))
  const nextContent = normalizeEditorText(content)
  if (currentContent === nextContent) return

  editor.value.commands.setContent(plainTextToHtml(nextContent), false)
}

const saveChapter = async () => {
  await workspace.saveEditorChapter()
  ElMessage.success('章节已保存')
}

const runAiAction = async (action) => {
  await workspace.runEditorAiAction(action)
  await revealAiResult(action)
  const messageMap = {
    continue: 'AI 续写结果已回流到右侧候选区',
    generate: '生成结果已回流到右侧候选区',
    optimize: '去模板化结果已回流到右侧候选区',
    rewrite: '改写结果已回流到右侧候选区',
    analyze: '审查结果已回流到右侧问题区'
  }
  ElMessage.success(messageMap[action] || 'AI 任务已提交')
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
  workspaceStore.setCurrentObject({
    type: 'issue',
    index,
    code: issue?.code || '',
    title: issue?.title || ''
  })

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
    workspaceStore.currentChapterId = payload.chapterId
    workspaceStore.setCurrentObject({
      type: 'chapter',
      id: payload.chapterId,
      title: payload.title || editorState.chapter.title || ''
    })
    workspace.openSection?.('chapters')
    return
  }

  if (payload.type === 'arc') {
    workspaceStore.setStructureSection('plot_arc')
    workspaceStore.setCurrentObject({
      type: 'plot_arc',
      arcId: payload.arcId || '',
      title: payload.title || ''
    })
    workspace.openSection?.('structure')
    return
  }

  if (payload.type === 'task-filter') {
    workspaceStore.setTaskFilter(payload.filter || 'all')
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
    clearIssueHighlight()
    void workspace.loadEditorChapter(chapterId)
  },
  { immediate: true }
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
