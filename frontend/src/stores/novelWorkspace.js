import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'

import { chapterEditorApi, contentApi, novelApi, projectApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'

const createEmptyEditorState = () => ({
  loading: false,
  saving: false,
  aiRunning: false,
  dirty: false,
  activeDraftTab: 'structural',
  chapter: {
    id: '',
    title: '',
    content: ''
  },
  outline: {},
  chapterTask: {},
  chapterArcs: [],
  contextMeta: {},
  structuralDraft: null,
  detemplatedDraft: null,
  integrityCheck: null
})

const normalizeIntegrityCheck = (payload = {}) => ({
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
  risk_notes: [],
  ...payload
})

const buildIntegrityCheckFromResult = (result = {}) => {
  if (result?.integrity_check && typeof result.integrity_check === 'object') {
    return normalizeIntegrityCheck({
      ...result.integrity_check,
      revision_attempts: result.integrity_check.revision_attempts || result.revision_attempts || []
    })
  }

  const notes = Array.isArray(result?.analysis?.continuity_risks)
    ? result.analysis.continuity_risks
    : []

  if (!notes.length) {
    return null
  }

  return normalizeIntegrityCheck({ risk_notes: notes })
}

export const useNovelWorkspaceStore = defineStore('novelWorkspace', () => {
  const loading = ref(false)
  const structureLoading = ref(false)
  const errorMessage = ref('')
  const novel = ref(null)
  const project = ref(null)
  const projectId = ref('')
  const chapters = ref([])
  const organizeProgress = ref({})
  const memoryView = ref({})
  const activeArcs = ref([])
  const copilotTab = ref('context')
  const editor = reactive(createEmptyEditorState())

  const resetEditor = () => {
    Object.assign(editor, createEmptyEditorState())
  }

  const syncChapterSnapshot = (chapterPatch) => {
    if (!chapterPatch?.id) return
    chapters.value = (chapters.value || []).map((item) => (
      item.id === chapterPatch.id
        ? { ...item, ...chapterPatch }
        : item
    ))
  }

  const markEditorDirty = (value = true) => {
    editor.dirty = Boolean(value)
  }

  const loadStructure = async () => {
    if (!projectId.value) {
      memoryView.value = {}
      activeArcs.value = []
      return
    }

    structureLoading.value = true
    try {
      const [nextMemoryView, arcResult] = await Promise.all([
        projectApi.memoryViewV2(projectId.value).catch(() => ({})),
        projectApi.activePlotArcsV2(projectId.value).catch(() => ({}))
      ])
      memoryView.value = nextMemoryView || {}
      activeArcs.value = arcResult?.plot_arcs || []
    } finally {
      structureLoading.value = false
    }
  }

  const loadBase = async (novelId) => {
    loading.value = true
    errorMessage.value = ''
    try {
      const [nextNovel, nextChapters, nextProject, nextProgress] = await Promise.all([
        novelApi.get(novelId),
        novelApi.listChapters(novelId),
        projectApi.getByNovel(novelId).catch(() => null),
        contentApi.organizeProgress(novelId).catch(() => ({}))
      ])

      novel.value = nextNovel
      chapters.value = nextChapters || []
      project.value = nextProject
      projectId.value = nextProject?.id || ''
      organizeProgress.value = nextProgress || {}

      await loadStructure()
    } catch (error) {
      errorMessage.value = error?.message || '加载新工作区失败。'
    } finally {
      loading.value = false
    }
  }

  const loadEditorChapter = async (chapterId) => {
    if (!chapterId) {
      resetEditor()
      return
    }

    editor.loading = true
    try {
      const [chapter, nextOutline, nextContext] = await Promise.all([
        chapterEditorApi.get(chapterId),
        chapterEditorApi.getOutline(chapterId).catch(() => ({})),
        chapterEditorApi.getContext(chapterId).catch(() => ({}))
      ])

      let nextTask = nextContext?.chapter_task_seed || {}
      let nextArcs = []
      if (projectId.value) {
        const [tasks, arcBindings] = await Promise.all([
          projectApi.chapterTasksV2(projectId.value).catch(() => []),
          projectApi.chapterArcsV2(chapterId).catch(() => ({}))
        ])

        nextTask = (tasks || []).find((item) => (
          item.chapter_id === chapterId || item.chapter_number === nextContext?.chapter_number
        )) || nextTask
        nextArcs = arcBindings?.bindings || []
      }

      editor.chapter = {
        id: chapter.id,
        title: chapter.title || '',
        content: chapter.content || ''
      }
      editor.outline = nextOutline || {}
      editor.contextMeta = nextContext || {}
      editor.chapterTask = nextTask || {}
      editor.chapterArcs = nextArcs
      editor.structuralDraft = chapter.structural_draft || null
      editor.detemplatedDraft = chapter.detemplated_draft || null
      editor.integrityCheck = chapter.integrity_check
        ? normalizeIntegrityCheck(chapter.integrity_check)
        : null
      editor.activeDraftTab = editor.detemplatedDraft ? 'detemplated' : 'structural'
      editor.dirty = false
    } finally {
      editor.loading = false
    }
  }

  const saveEditorChapter = async () => {
    if (!editor.chapter.id) return null

    editor.saving = true
    try {
      const result = await chapterEditorApi.save(editor.chapter.id, {
        title: editor.chapter.title,
        content: editor.chapter.content
      })

      syncChapterSnapshot({
        id: editor.chapter.id,
        title: editor.chapter.title,
        content: editor.chapter.content,
        updated_at: new Date().toISOString()
      })
      editor.dirty = false

      return result
    } finally {
      editor.saving = false
    }
  }

  const buildEditorPayload = () => ({
    title: editor.chapter.title,
    content: editor.chapter.content,
    outline: editor.outline,
    global_memory_summary: editor.contextMeta.last_chapter_tail || '',
    global_outline_summary: editor.contextMeta.chapter_outline?.goal || '',
    recent_chapter_summaries: (editor.contextMeta.recent_chapter_memories || []).map((item) => (
      item.scene_summary || item.chapter_title || ''
    ))
  })

  const runEditorAiAction = async (action) => {
    if (!editor.chapter.id) return null

    const workspaceStore = useWorkspaceStore()
    const taskMetaMap = {
      continue: { type: 'writing', label: 'AI 续写', resultType: 'candidate' },
      optimize: { type: 'rewrite', label: 'AI 去模板化', resultType: 'diff' },
      rewrite: { type: 'rewrite', label: 'AI 风格改写', resultType: 'diff' },
      generate: { type: 'writing', label: '根据大纲生成', resultType: 'candidate' },
      analyze: { type: 'audit', label: 'AI 审查', resultType: 'issues' }
    }
    const taskMeta = taskMetaMap[action] || { type: action, label: action, resultType: 'none' }
    const taskId = `editor-${action}-${Date.now()}`

    editor.aiRunning = true
    workspaceStore.setCurrentTask({
      id: taskId,
      type: taskMeta.type,
      label: taskMeta.label,
      status: 'running',
      chapterId: editor.chapter.id,
      resultType: taskMeta.resultType
    })
    try {
      const payload = buildEditorPayload()
      let result = null

      if (action === 'continue') {
        result = await chapterEditorApi.continueWrite(editor.chapter.id, payload)
        editor.structuralDraft = {
          title: editor.chapter.title || 'AI 结构稿',
          content: result?.result_text || ''
        }
        editor.activeDraftTab = 'structural'
      } else if (action === 'optimize') {
        result = await chapterEditorApi.optimize(editor.chapter.id, payload)
        editor.detemplatedDraft = {
          title: editor.chapter.title || 'AI 改写稿',
          content: result?.result_text || '',
          display_fallback_to_structural: false
        }
        editor.activeDraftTab = 'detemplated'
      } else if (action === 'rewrite') {
        result = await chapterEditorApi.rewriteStyle(editor.chapter.id, payload)
        editor.detemplatedDraft = {
          title: editor.chapter.title || 'AI 改写稿',
          content: result?.result_text || '',
          display_fallback_to_structural: false
        }
        editor.activeDraftTab = 'detemplated'
      } else if (action === 'generate') {
        result = await chapterEditorApi.generateFromOutline(editor.chapter.id, payload)
        editor.structuralDraft = {
          title: editor.chapter.title || 'AI 结构稿',
          content: result?.result_text || ''
        }
        if (result?.outline_draft) {
          editor.outline = { ...editor.outline, ...result.outline_draft }
        }
        editor.activeDraftTab = 'structural'
      } else if (action === 'analyze') {
        result = await chapterEditorApi.analyze(editor.chapter.id, payload)
        editor.activeDraftTab = 'integrity'
      }

      const integrityCheck = buildIntegrityCheckFromResult(result || {})
      if (integrityCheck) {
        editor.integrityCheck = integrityCheck
      }

      workspaceStore.setCurrentTask({
        id: taskId,
        type: taskMeta.type,
        label: taskMeta.label,
        status: 'completed',
        chapterId: editor.chapter.id,
        resultType: taskMeta.resultType
      })
      return result
    } catch (error) {
      workspaceStore.setCurrentTask({
        id: taskId,
        type: taskMeta.type,
        label: taskMeta.label,
        status: 'failed',
        chapterId: editor.chapter.id,
        resultType: taskMeta.resultType,
        error: error?.message || 'AI 任务失败'
      })
      throw error
    } finally {
      editor.aiRunning = false
    }
  }

  const applyDraftToEditor = ({ type, mode }) => {
    const draft = type === 'detemplated' ? editor.detemplatedDraft : editor.structuralDraft
    if (!draft?.content) return false

    editor.chapter.title = draft.title || editor.chapter.title
    editor.chapter.content = mode === 'append'
      ? `${editor.chapter.content || ''}\n\n${draft.content}`.trim()
      : draft.content
    editor.dirty = true
    return true
  }

  const saveDraftResult = async ({ type }) => {
    const applied = applyDraftToEditor({ type, mode: 'replace' })
    if (!applied) return false
    await saveEditorChapter()
    return true
  }

  const discardDraft = ({ type }) => {
    if (type === 'detemplated') editor.detemplatedDraft = null
    if (type === 'structural') editor.structuralDraft = null
  }

  return {
    loading,
    structureLoading,
    errorMessage,
    novel,
    project,
    projectId,
    chapters,
    organizeProgress,
    memoryView,
    activeArcs,
    copilotTab,
    editor,
    resetEditor,
    syncChapterSnapshot,
    markEditorDirty,
    loadBase,
    loadStructure,
    loadEditorChapter,
    saveEditorChapter,
    runEditorAiAction,
    applyDraftToEditor,
    saveDraftResult,
    discardDraft
  }
})
