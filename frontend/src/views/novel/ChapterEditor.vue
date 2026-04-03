<template>
  <div class="chapter-editor-page" v-loading="state.loading">
    <el-page-header :content="pageTitle" @back="goBack" />

    <el-alert v-if="state.errorMessage" :title="state.errorMessage" type="error" show-icon :closable="false" />

    <el-row :gutter="16" class="editor-grid">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>正文编辑区</span>
              <div class="header-actions">
                <el-button :loading="state.saving" @click="saveChapter('draft')">保存草稿</el-button>
                <el-button type="primary" :loading="state.saving" @click="saveChapter('saved')">保存章节</el-button>
              </div>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="标题">
              <el-input v-model="state.chapter.title" placeholder="请输入章节标题" />
            </el-form-item>
            <el-form-item label="正文">
              <el-input v-model="state.chapter.content" type="textarea" :rows="24" placeholder="请输入或采纳正文" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-space direction="vertical" fill :size="16" class="right-column">
          <el-card shadow="never">
            <template #header>
              <div class="header-row">
                <span>本章大纲区</span>
                <div class="header-actions">
                  <el-button @click="saveOutline">保存大纲</el-button>
                  <el-button type="primary" :loading="state.aiRunning" @click="runAiAction('generate')">按大纲生成</el-button>
                </div>
              </div>
            </template>
            <el-form label-position="top">
              <el-form-item label="本章目标">
                <el-input v-model="state.outline.goal" />
              </el-form-item>
              <el-form-item label="核心冲突">
                <el-input v-model="state.outline.conflict" />
              </el-form-item>
              <el-form-item label="关键事件">
                <el-input v-model="outlineEventsText" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="人物推进">
                <el-input v-model="state.outline.character_progress" />
              </el-form-item>
              <el-form-item label="结尾钩子">
                <el-input v-model="state.outline.ending_hook" />
              </el-form-item>
              <el-form-item label="开头承接点">
                <el-input v-model="state.outline.opening_continuation" />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="state.outline.notes" type="textarea" :rows="2" />
              </el-form-item>
            </el-form>
          </el-card>

          <ChapterTaskCard :task="state.chapterTask" />

          <el-card shadow="never">
            <template #header>
              <span>本章所属剧情弧</span>
            </template>
            <el-empty v-if="!state.chapterArcs.length" description="暂无绑定剧情弧" />
            <el-radio-group v-if="state.chapterArcs.length" v-model="arcTypeFilter" class="top-gap">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="main_arc">主线弧</el-radio-button>
              <el-radio-button label="character_arc">人物弧</el-radio-button>
              <el-radio-button label="supporting_arc">支线弧</el-radio-button>
            </el-radio-group>
            <el-descriptions v-else :column="1" border>
              <el-descriptions-item v-for="item in filteredChapterArcs" :key="item.binding_id" :label="item.arc_id">
                <div>角色：{{ item.binding_role || 'background' }}</div>
                <div>推进：{{ item.push_type || 'advance' }}</div>
                <div>绑定置信度：{{ item.confidence ?? 0 }}</div>
                <div v-if="item.latest_snapshot?.stage_before || item.latest_snapshot?.stage_after">
                  最近迁移：{{ item.latest_snapshot?.stage_before || '未知' }} -> {{ item.latest_snapshot?.stage_after || '未知' }}
                </div>
                <div v-if="item.latest_snapshot?.progress_summary">迁移证据：{{ item.latest_snapshot?.progress_summary }}</div>
                <div v-if="item.latest_snapshot?.change_reason">迁移原因：{{ item.latest_snapshot?.change_reason }}</div>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <span>AI 工具区</span>
            </template>
            <div class="tool-grid">
              <el-button @click="openImportDialog">导入章节</el-button>
              <el-button :loading="state.aiRunning" @click="runAiAction('analyze')">分析</el-button>
              <el-button :loading="state.aiRunning" @click="runAiAction('continue')">续写</el-button>
              <el-button :loading="state.aiRunning" @click="runAiAction('optimize')">优化</el-button>
              <el-button :loading="state.aiRunning" @click="runAiAction('rewrite')">风格改写</el-button>
              <el-button type="primary" :loading="state.aiRunning" @click="runAiAction('generate')">按大纲生成</el-button>
            </div>
          </el-card>

          <ContextSourcePanel :context="state.contextMeta" :task="state.chapterTask" />
        </el-space>
      </el-col>

      <el-col :span="24">
        <DraftPreviewTabs
          title="AI 结果区"
          v-model:active-tab="state.activeDraftTab"
          :structural-draft="state.structuralDraft"
          :detemplated-draft="state.detemplatedDraft"
          :integrity-check="state.integrityCheck"
          :revision-attempts="state.integrityCheck?.revision_attempts || []"
          :used-structural-fallback="Boolean(state.detemplatedDraft?.display_fallback_to_structural)"
          @apply="applyDraft"
          @save-draft="saveDraftResult"
          @discard="discardDraft"
        />
      </el-col>
    </el-row>

    <el-dialog v-model="state.importDialogVisible" title="导入章节" width="720px">
      <el-alert title="如果当前正文已有内容，导入后将覆盖当前编辑区。" type="warning" :closable="false" show-icon />
      <div class="tool-grid top-gap">
        <el-upload :auto-upload="false" :show-file-list="false" accept=".txt,.md" :on-change="handleImportFileChange">
          <el-button>上传文件</el-button>
        </el-upload>
        <el-button v-if="canRestoreOriginal" @click="restoreOriginalContent">恢复原文</el-button>
      </div>
      <el-input v-model="state.importText" type="textarea" :rows="16" placeholder="支持粘贴文本或文件内容" class="top-gap" />
      <template #footer>
        <el-button @click="state.importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="state.aiRunning" @click="importChapter">执行导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, getCurrentInstance, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { chapterEditorApi, novelApi, projectApi } from '@/api'
import ChapterTaskCard from '@/components/story/ChapterTaskCard.vue'
import ContextSourcePanel from '@/components/story/ContextSourcePanel.vue'
import DraftPreviewTabs from '@/components/story/DraftPreviewTabs.vue'
import { useChapterEditorState } from '@/composables/useChapterEditorState'

const route = useRoute()
const { proxy } = getCurrentInstance()
const state = useChapterEditorState()
const originalChapterSnapshot = ref(null)
const arcTypeFilter = ref('all')
const arcTypeFilterStorageKey = computed(() => `inktrace:arc-type:${route.params.id || 'unknown'}`)
const isCreateMode = computed(() => !route.params.chapterId)
const pageTitle = computed(() => (isCreateMode.value ? '新建章节' : `编辑章节：${state.chapter.title || '未命名章节'}`))
const canRestoreOriginal = computed(() => Boolean(originalChapterSnapshot.value))
const filteredChapterArcs = computed(() => {
  if (arcTypeFilter.value === 'all') return state.chapterArcs || []
  return (state.chapterArcs || []).filter((item) => {
    const arcType = item?.arc_type || item?.arc?.arc_type || item?.latest_snapshot?.arc_type || ''
    return String(arcType) === arcTypeFilter.value
  })
})
const outlineEventsText = computed({
  get: () => (state.outline.events || []).join('\n'),
  set: (value) => {
    state.outline.events = String(value || '')
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)
  }
})

const loadChapter = async () => {
  if (isCreateMode.value) {
    state.chapter = { id: '', title: '', content: '' }
    return
  }
  const chapter = await chapterEditorApi.get(route.params.chapterId)
  state.chapter = {
    id: chapter.id,
    title: chapter.title,
    content: chapter.content
  }
}

const loadOutline = async () => {
  if (isCreateMode.value) {
    state.outline = {}
    return
  }
  try {
    state.outline = await chapterEditorApi.getOutline(route.params.chapterId)
  } catch {
    state.outline = {}
  }
}

const loadContextAndTask = async () => {
  if (isCreateMode.value) {
    state.contextMeta = {}
    state.chapterTask = {}
    return
  }
  try {
    state.contextMeta = await chapterEditorApi.getContext(route.params.chapterId)
    const project = await projectApi.getByNovel(route.params.id)
    if (project?.id) {
      const tasks = await projectApi.chapterTasksV2(project.id)
      const matched = (tasks || []).find((item) => item.chapter_id === route.params.chapterId || item.chapter_number === state.contextMeta.chapter_number)
      state.chapterTask = matched || state.contextMeta.chapter_task_seed || {}
      const arcBindings = await projectApi.chapterArcsV2(route.params.chapterId)
      state.chapterArcs = arcBindings?.bindings || []
    }
  } catch {
    state.contextMeta = {}
    state.chapterTask = {}
    state.chapterArcs = []
  }
}

const initialize = async () => {
  state.loading = true
  try {
    await Promise.all([loadChapter(), loadOutline()])
    await loadContextAndTask()
    state.errorMessage = ''
  } catch (error) {
    state.errorMessage = error?.message || '加载章节编辑页失败'
  } finally {
    state.loading = false
  }
}

const loadArcTypeFilterPreference = () => {
  const saved =
    window.localStorage.getItem(arcTypeFilterStorageKey.value) ||
    window.localStorage.getItem(`inktrace:chapter-arc-type:${route.params.id || 'unknown'}`) ||
    'all'
  arcTypeFilter.value = ['all', 'main_arc', 'character_arc', 'supporting_arc'].includes(saved) ? saved : 'all'
}

const saveChapter = async () => {
  state.saving = true
  try {
    if (isCreateMode.value) {
      const created = await novelApi.createChapter(route.params.id, {
        title: state.chapter.title,
        content: state.chapter.content
      })
      ElMessage.success('章节已保存，但全局摘要尚未刷新')
      proxy?.$router?.push(`/novel/${route.params.id}/chapters/${created.id}/edit`)
      return
    }
    await chapterEditorApi.save(route.params.chapterId, {
      title: state.chapter.title,
      content: state.chapter.content
    })
    ElMessage.success('章节已保存，但全局摘要尚未刷新')
  } finally {
    state.saving = false
  }
}

const saveOutline = async () => {
  if (isCreateMode.value) {
    ElMessage.warning('请先保存章节，再保存大纲')
    return
  }
  await chapterEditorApi.saveOutline(route.params.chapterId, state.outline)
  ElMessage.success('本章大纲已保存')
}

const normalizeIntegrityCheck = (notes = []) => ({
  event_integrity_ok: true,
  motivation_integrity_ok: true,
  foreshadowing_integrity_ok: true,
  hook_integrity_ok: true,
  continuity_ok: true,
  arc_consistency_ok: true,
  title_alignment_ok: true,
  progression_integrity_ok: true,
  issue_list: [],
  revision_attempts: [],
  risk_notes: Array.isArray(notes) ? notes : []
})

const runAiAction = async (action) => {
  if (isCreateMode.value) {
    ElMessage.warning('请先保存章节，再执行 AI 操作')
    return
  }
  state.aiRunning = true
  try {
    const payload = {
      title: state.chapter.title,
      content: state.chapter.content,
      outline: state.outline,
      global_memory_summary: state.contextMeta.last_chapter_tail || '',
      global_outline_summary: state.contextMeta.chapter_outline?.goal || '',
      recent_chapter_summaries: (state.contextMeta.recent_chapter_memories || []).map((item) => item.scene_summary || item.chapter_title || '')
    }
    if (action === 'continue') {
      const result = await chapterEditorApi.continueWrite(route.params.chapterId, payload)
      state.structuralDraft = { title: state.chapter.title || 'AI 结构稿', content: result.result_text || '' }
      state.activeDraftTab = 'structural'
    } else if (action === 'optimize') {
      const result = await chapterEditorApi.optimize(route.params.chapterId, payload)
      state.detemplatedDraft = { title: state.chapter.title || 'AI 改写稿', content: result.result_text || '', display_fallback_to_structural: false }
      state.activeDraftTab = 'detemplated'
    } else if (action === 'rewrite') {
      const result = await chapterEditorApi.rewriteStyle(route.params.chapterId, payload)
      state.detemplatedDraft = { title: state.chapter.title || 'AI 改写稿', content: result.result_text || '', display_fallback_to_structural: false }
      state.activeDraftTab = 'detemplated'
    } else if (action === 'generate') {
      const result = await chapterEditorApi.generateFromOutline(route.params.chapterId, payload)
      state.structuralDraft = { title: state.chapter.title || 'AI 结构稿', content: result.result_text || '' }
      if (result.outline_draft) state.outline = { ...state.outline, ...result.outline_draft }
      state.activeDraftTab = 'structural'
    } else if (action === 'analyze') {
      const result = await chapterEditorApi.analyze(route.params.chapterId, payload)
      state.integrityCheck = normalizeIntegrityCheck(result.analysis?.continuity_risks || [])
      state.activeDraftTab = 'integrity'
    }
  } finally {
    state.aiRunning = false
  }
}

const openImportDialog = () => {
  state.importDialogVisible = true
}

const handleImportFileChange = (file) => {
  const raw = file?.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = () => {
    state.importText = String(reader.result || '')
  }
  reader.readAsText(raw, 'utf-8')
}

const importChapter = async () => {
  if (isCreateMode.value) {
    ElMessage.warning('请先创建章节，再执行导入')
    return
  }
  if (state.chapter.content?.trim()) {
    await ElMessageBox.confirm('当前正文已有内容，导入后将覆盖当前编辑区，是否继续？', '覆盖确认', { type: 'warning' })
  }
  state.aiRunning = true
  try {
    originalChapterSnapshot.value = {
      title: state.chapter.title,
      content: state.chapter.content
    }
    const result = await chapterEditorApi.importChapter(route.params.chapterId, {
      raw_text: state.importText,
      title: state.chapter.title,
      recent_chapter_summaries: (state.contextMeta.recent_chapter_memories || []).map((item) => item.scene_summary || item.chapter_title || '')
    })
    state.chapter.title = result.title || state.chapter.title
    state.chapter.content = result.content || state.chapter.content
    if (result.outline_draft) state.outline = { ...state.outline, ...result.outline_draft }
    state.importDialogVisible = false
    ElMessage.success('已自动生成本章大纲草稿，请确认后继续编辑')
  } finally {
    state.aiRunning = false
  }
}

const restoreOriginalContent = () => {
  if (!originalChapterSnapshot.value) return
  state.chapter.title = originalChapterSnapshot.value.title
  state.chapter.content = originalChapterSnapshot.value.content
  ElMessage.success('已恢复导入前原文')
}

const applyDraft = ({ type, mode }) => {
  const draft = type === 'detemplated' ? state.detemplatedDraft : state.structuralDraft
  if (!draft?.content) return
  state.chapter.title = draft.title || state.chapter.title
  state.chapter.content = mode === 'append' ? `${state.chapter.content || ''}\n\n${draft.content}`.trim() : draft.content
  ElMessage.success('AI 结果已采纳到正文编辑区')
}

const saveDraftResult = ({ type }) => {
  const draft = type === 'detemplated' ? state.detemplatedDraft : state.structuralDraft
  if (!draft?.content) return
  state.chapter.title = draft.title || state.chapter.title
  state.chapter.content = draft.content
  saveChapter()
}

const discardDraft = ({ type }) => {
  if (type === 'detemplated') state.detemplatedDraft = null
  if (type === 'structural') state.structuralDraft = null
}

const goBack = () => {
  proxy?.$router?.push(`/novel/${route.params.id}`)
}

onMounted(async () => {
  loadArcTypeFilterPreference()
  await initialize()
})

watch(arcTypeFilter, (value) => {
  window.localStorage.setItem(arcTypeFilterStorageKey.value, value || 'all')
})
</script>

<style scoped>
.chapter-editor-page {
  padding: 20px;
}

.editor-grid {
  margin-top: 16px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-actions,
.tool-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.right-column {
  width: 100%;
}

.top-gap {
  margin-top: 16px;
}
</style>
