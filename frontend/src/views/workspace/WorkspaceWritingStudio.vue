<template>
  <div class="workspace-page">
    <section class="workspace-section editor-shell">
      <div class="editor-topbar">
        <div>
          <div class="eyebrow">Writing Studio</div>
          <h2>{{ editorState.chapter.title || '选择一个章节开始写作' }}</h2>
          <p>{{ chapterSummary }}</p>
        </div>
        <div class="editor-actions">
          <el-button v-if="editorState.chapter.id" @click="openLegacyEditor">旧版编辑器</el-button>
          <el-button
            v-if="editorState.chapter.id"
            :loading="editorState.saving"
            type="primary"
            @click="saveChapter"
          >
            保存正文
          </el-button>
        </div>
      </div>

      <div v-if="editorState.loading" class="editor-loading">
        <el-skeleton :rows="10" animated />
      </div>

      <el-empty
        v-else-if="!editorState.chapter.id"
        description="还没有选中章节。可以从左侧目录或章节台打开一个章节。"
      />

      <template v-else>
        <div class="field-row">
          <label class="field-label" for="chapter-title">章节标题</label>
          <input
            id="chapter-title"
            v-model="editorState.chapter.title"
            class="title-input"
            type="text"
            placeholder="输入章节标题"
            @input="workspace.state.markEditorDirty()"
          />
        </div>

        <div class="editor-toolbar">
          <span class="toolbar-chip">TipTap 编辑器</span>
          <span class="toolbar-chip">候选稿 / diff / issue 已回流</span>
          <button type="button" class="toolbar-link" @click="workspace.openSection('tasks')">查看任务与审查</button>
          <button type="button" class="toolbar-link" @click="workspace.openSection('structure')">查看结构</button>
        </div>

        <div class="command-toolbar">
          <el-button :loading="editorState.aiRunning" @click="runAiAction('analyze')">审查</el-button>
          <el-button :loading="editorState.aiRunning" @click="runAiAction('continue')">续写</el-button>
          <el-button :loading="editorState.aiRunning" @click="runAiAction('optimize')">优化</el-button>
          <el-button :loading="editorState.aiRunning" @click="runAiAction('rewrite')">风格改写</el-button>
          <el-button type="primary" :loading="editorState.aiRunning" @click="runAiAction('generate')">按大纲生成</el-button>
        </div>

        <div class="studio-grid">
          <div class="editor-panel">
            <editor-content :editor="editor" class="editor-surface" />
            <div class="editor-footer">
              <span>{{ wordCount }} 字</span>
              <span v-if="editorState.aiRunning">AI 正在处理当前章节</span>
              <span v-else-if="editorState.dirty">尚未保存</span>
              <span v-else>已与本地状态同步</span>
            </div>
          </div>

          <aside class="context-column">
            <ChapterTaskCard :task="editorState.chapterTask" title="当前章节任务" />
            <ContextSourcePanel :context="editorState.contextMeta" :task="editorState.chapterTask" />
            <section class="context-card">
              <div class="context-card-title">绑定剧情弧</div>
              <div v-if="editorState.chapterArcs.length" class="arc-mini-list">
                <div v-for="arc in editorState.chapterArcs.slice(0, 4)" :key="arc.binding_id || arc.arc_id" class="arc-mini-item">
                  <strong>{{ arc.arc?.title || arc.arc_id || '未命名剧情弧' }}</strong>
                  <span>{{ arc.push_type || 'advance' }} · {{ arc.binding_role || 'background' }}</span>
                </div>
              </div>
              <p v-else>当前章节还没有绑定剧情弧，后续会由结构台继续补强。</p>
            </section>
          </aside>
        </div>

        <div class="result-grid">
          <DraftPreviewTabs
            title="写作台结果区"
            v-model:active-tab="editorState.activeDraftTab"
            :structural-draft="editorState.structuralDraft"
            :detemplated-draft="editorState.detemplatedDraft"
            :integrity-check="editorState.integrityCheck"
            :revision-attempts="editorState.integrityCheck?.revision_attempts || []"
            :used-structural-fallback="Boolean(editorState.detemplatedDraft?.display_fallback_to_structural)"
            @apply="applyDraft"
            @save-draft="saveDraftResult"
            @discard="discardDraft"
          />

          <section class="review-panel">
            <div class="review-header">
              <div>
                <h3>diff / issue 面板</h3>
                <p>候选稿和审查结果不再散落到旧页面，先在写作台内完成预览、采纳和定位。</p>
              </div>
            </div>

            <el-tabs v-model="inspectorTab">
              <el-tab-pane label="差异" name="diff">
                <div v-if="!activeDraft" class="empty-review">暂无候选稿。可以先点击续写、优化或按大纲生成。</div>
                <template v-else>
                  <div class="diff-summary">
                    <span>{{ activeDraft.label }}</span>
                    <span>新增 {{ diffStats.added }} 行</span>
                    <span>移除 {{ diffStats.removed }} 行</span>
                  </div>
                  <div class="diff-list">
                    <div
                      v-for="(row, index) in diffRows"
                      :key="`${row.type}-${index}-${row.text}`"
                      class="diff-row"
                      :class="row.type"
                    >
                      <span class="diff-sign">{{ diffSignMap[row.type] }}</span>
                      <span class="diff-text">{{ row.text || ' ' }}</span>
                    </div>
                  </div>
                  <div v-if="diffTruncated" class="empty-review">差异内容较长，当前只展示前 160 行。</div>
                </template>
              </el-tab-pane>

              <el-tab-pane label="问题" name="issues">
                <div v-if="!issueList.length && !riskNotes.length" class="empty-review">暂无 issue 或风险说明。</div>
                <div v-else class="issue-list">
                  <el-alert
                    v-for="(item, index) in issueList"
                    :key="`${item.code || 'issue'}-${index}`"
                    :title="item.title || '未命名问题'"
                    :description="item.detail || ''"
                    :type="severityType(item.severity)"
                    :closable="false"
                    show-icon
                  />
                  <el-alert
                    v-for="(note, index) in riskNotes"
                    :key="`risk-${index}`"
                    :title="note"
                    type="warning"
                    :closable="false"
                    show-icon
                  />
                </div>
              </el-tab-pane>
            </el-tabs>
          </section>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

import ChapterTaskCard from '@/components/story/ChapterTaskCard.vue'
import ContextSourcePanel from '@/components/story/ContextSourcePanel.vue'
import DraftPreviewTabs from '@/components/story/DraftPreviewTabs.vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const route = useRoute()
const router = useRouter()
const workspace = useWorkspaceContext()
const editorState = workspace.state.editor
const inspectorTab = ref('diff')
const syncingFromStore = ref(false)
const diffSignMap = {
  unchanged: ' ',
  added: '+',
  removed: '-'
}

const selectedChapterId = computed(() => String(route.query.chapterId || workspace.currentChapterId.value || ''))

const chapterSummary = computed(() => {
  if (!editorState.chapter.id) return '新工作区第一阶段先把章节打开、编辑和保存链打通。'
  return (
    editorState.outline?.goal ||
    editorState.contextMeta?.continuation_goal ||
    editorState.contextMeta?.summary ||
    '当前写作台已接入 TipTap、候选稿、差异预览和 issue 回流。'
  )
})

const wordCount = computed(() => (editorState.chapter.content || '').replace(/\s+/g, '').length)

const activeDraft = computed(() => {
  if (editorState.activeDraftTab === 'detemplated' && editorState.detemplatedDraft) {
    return { ...editorState.detemplatedDraft, label: '去模板化稿' }
  }
  if (editorState.activeDraftTab === 'structural' && editorState.structuralDraft) {
    return { ...editorState.structuralDraft, label: '结构稿' }
  }
  if (editorState.detemplatedDraft) {
    return { ...editorState.detemplatedDraft, label: '去模板化稿' }
  }
  if (editorState.structuralDraft) {
    return { ...editorState.structuralDraft, label: '结构稿' }
  }
  return null
})

const allDiffRows = computed(() => buildLineDiff(editorState.chapter.content, activeDraft.value?.content || ''))
const diffRows = computed(() => allDiffRows.value.slice(0, 160))
const diffTruncated = computed(() => allDiffRows.value.length > diffRows.value.length)
const diffStats = computed(() => ({
  added: allDiffRows.value.filter((row) => row.type === 'added').length,
  removed: allDiffRows.value.filter((row) => row.type === 'removed').length
}))

const issueList = computed(() => (
  Array.isArray(editorState.integrityCheck?.issue_list)
    ? editorState.integrityCheck.issue_list
    : []
))
const riskNotes = computed(() => (
  Array.isArray(editorState.integrityCheck?.risk_notes)
    ? editorState.integrityCheck.risk_notes
    : []
))

const editor = useEditor({
  extensions: [
    StarterKit,
    Placeholder.configure({
      placeholder: '开始写作，或者从左侧打开已有章节。'
    })
  ],
  content: '',
  editorProps: {
    attributes: {
      class: 'tiptap-editor'
    }
  },
  onUpdate: ({ editor: nextEditor }) => {
    if (syncingFromStore.value) return
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

  syncingFromStore.value = true
  editor.value.commands.setContent(plainTextToHtml(nextContent), false)
  syncingFromStore.value = false
}

const saveChapter = async () => {
  await workspace.saveEditorChapter()
  ElMessage.success('章节已保存到新的工作区流程中。')
}

const runAiAction = async (action) => {
  const actionLabel = {
    analyze: '审查',
    continue: '续写',
    optimize: '优化',
    rewrite: '风格改写',
    generate: '按大纲生成'
  }[action] || 'AI 操作'

  const result = await workspace.runEditorAiAction(action)
  if (result) {
    inspectorTab.value = action === 'analyze' ? 'issues' : 'diff'
    ElMessage.success(`${actionLabel}完成，结果已回流到写作台。`)
  }
}

const applyDraft = (payload) => {
  const applied = workspace.applyDraftToEditor(payload)
  if (!applied) {
    ElMessage.warning('暂无可采纳的候选稿')
    return
  }
  ElMessage.success('AI 结果已采纳到当前正文。')
}

const saveDraftResult = async (payload) => {
  const saved = await workspace.saveDraftResult(payload)
  if (!saved) {
    ElMessage.warning('暂无可保存的候选稿')
    return
  }
  ElMessage.success('候选稿已保存为当前章节正文。')
}

const discardDraft = (payload) => {
  workspace.discardDraft(payload)
  ElMessage.success('已放弃当前候选稿。')
}

const openLegacyEditor = () => {
  if (!editorState.chapter.id) return
  router.push(`/novel/${route.params.id}/chapters/${editorState.chapter.id}/edit`)
}

const severityType = (severity) => {
  if (severity === 'high') return 'error'
  if (severity === 'medium') return 'warning'
  return 'info'
}

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

const buildIndexedDiff = (sourceLines, targetLines) => {
  const rows = []
  const maxLength = Math.max(sourceLines.length, targetLines.length)
  for (let index = 0; index < maxLength; index += 1) {
    const sourceLine = sourceLines[index]
    const targetLine = targetLines[index]
    if (sourceLine === targetLine) {
      rows.push({ type: 'unchanged', text: sourceLine || '' })
    } else {
      if (sourceLine !== undefined) rows.push({ type: 'removed', text: sourceLine })
      if (targetLine !== undefined) rows.push({ type: 'added', text: targetLine })
    }
  }
  return rows
}

const buildLineDiff = (sourceText = '', targetText = '') => {
  if (!targetText) return []
  const sourceLines = String(sourceText || '').split(/\r?\n/)
  const targetLines = String(targetText || '').split(/\r?\n/)

  if (sourceLines.length * targetLines.length > 60000) {
    return buildIndexedDiff(sourceLines, targetLines)
  }

  const table = Array.from({ length: sourceLines.length + 1 }, () => Array(targetLines.length + 1).fill(0))
  for (let i = sourceLines.length - 1; i >= 0; i -= 1) {
    for (let j = targetLines.length - 1; j >= 0; j -= 1) {
      table[i][j] = sourceLines[i] === targetLines[j]
        ? table[i + 1][j + 1] + 1
        : Math.max(table[i + 1][j], table[i][j + 1])
    }
  }

  const rows = []
  let i = 0
  let j = 0
  while (i < sourceLines.length && j < targetLines.length) {
    if (sourceLines[i] === targetLines[j]) {
      rows.push({ type: 'unchanged', text: sourceLines[i] })
      i += 1
      j += 1
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      rows.push({ type: 'removed', text: sourceLines[i] })
      i += 1
    } else {
      rows.push({ type: 'added', text: targetLines[j] })
      j += 1
    }
  }

  while (i < sourceLines.length) {
    rows.push({ type: 'removed', text: sourceLines[i] })
    i += 1
  }
  while (j < targetLines.length) {
    rows.push({ type: 'added', text: targetLines[j] })
    j += 1
  }

  return rows
}

watch(
  () => [selectedChapterId.value, workspace.state.projectId],
  ([chapterId]) => {
    void workspace.loadEditorChapter(chapterId)
  },
  { immediate: true }
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
.workspace-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.workspace-section {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 34px rgba(93, 72, 37, 0.07);
}

.editor-shell {
  display: flex;
  flex-direction: column;
  min-height: 72vh;
}

.editor-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a86c3b;
}

.editor-topbar h2 {
  margin-top: 8px;
  color: #342318;
}

.editor-topbar p {
  margin-top: 8px;
  line-height: 1.7;
  color: #6f5641;
}

.editor-actions,
.command-toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.field-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.field-label {
  font-size: 13px;
  font-weight: 700;
  color: #77593d;
}

.title-input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(90, 67, 44, 0.12);
  border-radius: 16px;
  font: inherit;
  font-size: 18px;
  background: #fffdf9;
  color: #2f2218;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.toolbar-chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(214, 150, 89, 0.12);
  color: #8b5c34;
  font-size: 12px;
}

.toolbar-link {
  border: none;
  background: none;
  color: #b96429;
  cursor: pointer;
  font: inherit;
}

.command-toolbar {
  margin-bottom: 16px;
}

.studio-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: stretch;
}

.editor-panel {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.editor-surface {
  flex: 1;
  min-height: 56vh;
  border-radius: 22px;
  background: linear-gradient(180deg, #fffdf9 0%, #fffaf1 100%);
  border: 1px solid rgba(90, 67, 44, 0.08);
  color: #2f2218;
  overflow: auto;
}

.editor-surface :deep(.tiptap-editor) {
  min-height: 56vh;
  padding: 28px 30px;
  outline: none;
  font-size: 18px;
  line-height: 1.9;
}

.editor-surface :deep(.tiptap-editor p) {
  margin: 0 0 0.9em;
}

.editor-surface :deep(.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  height: 0;
  color: #a58a71;
  pointer-events: none;
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  color: #8b6f54;
  font-size: 13px;
}

.context-column {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 14px;
}

.context-column :deep(.el-card) {
  border: 1px solid rgba(90, 67, 44, 0.08);
  border-radius: 18px;
  background: #fffaf2;
}

.context-card,
.review-panel {
  padding: 18px;
  border-radius: 18px;
  background: #fffaf2;
  border: 1px solid rgba(90, 67, 44, 0.08);
}

.context-card-title {
  font-weight: 700;
  color: #342318;
}

.context-card p,
.arc-mini-item span,
.review-header p,
.empty-review {
  margin-top: 8px;
  line-height: 1.7;
  color: #6f5641;
}

.arc-mini-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.arc-mini-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(244, 235, 222, 0.82);
}

.arc-mini-item strong {
  color: #3a291c;
}

.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: 18px;
  margin-top: 18px;
}

.review-panel h3 {
  color: #342318;
}

.diff-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.diff-summary span {
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(214, 150, 89, 0.12);
  color: #7c5432;
  font-size: 12px;
}

.diff-list {
  max-height: 420px;
  overflow: auto;
  border-radius: 14px;
  border: 1px solid rgba(90, 67, 44, 0.08);
  background: #fffdf9;
}

.diff-row {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(90, 67, 44, 0.05);
  font-family: "LXGW WenKai", "Noto Serif SC", serif;
  line-height: 1.65;
}

.diff-row.added {
  background: rgba(88, 148, 92, 0.11);
  color: #2d5f37;
}

.diff-row.removed {
  background: rgba(184, 89, 68, 0.11);
  color: #8b382e;
}

.diff-sign {
  opacity: 0.76;
  font-weight: 700;
}

.diff-text {
  white-space: pre-wrap;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.editor-loading {
  padding: 24px 0;
}

@media (max-width: 1280px) {
  .studio-grid,
  .result-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .editor-topbar {
    flex-direction: column;
  }
}
</style>
