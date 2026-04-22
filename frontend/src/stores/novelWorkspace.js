import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

import { chapterEditorApi, contentApi, novelApi, projectApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { buildWorkspaceTaskCenter, normalizeWorkspaceTaskResultType } from '@/views/workspace/workspaceTaskModel'

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
  integrityCheck: null,
  resultState: {
    latestTaskId: '',
    latestAction: '',
    latestResultType: 'none',
    latestDraftType: '',
    lastDecision: 'idle',
    lastUpdatedAt: '',
    latestIssueCount: 0,
    lastError: ''
  }
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

const buildDraftPayload = ({ title, action, currentContent, resultText, selectionContext = null }) => {
  const fullContent = String(resultText || '')
  const baseContent = String(currentContent || '')

  if (!fullContent) {
    return {
      title,
      content: '',
      full_content: '',
      preview_mode: 'empty',
      source_action: action,
      selection_context: selectionContext
    }
  }

  let sharedPrefix = 0
  const maxLength = Math.min(baseContent.length, fullContent.length)
  while (sharedPrefix < maxLength && baseContent[sharedPrefix] === fullContent[sharedPrefix]) {
    sharedPrefix += 1
  }

  const appendedContent = fullContent.slice(sharedPrefix).trimStart()
  const sharedRatio = baseContent.length ? sharedPrefix / baseContent.length : 0
  const shouldPreviewDelta = action === 'continue' && appendedContent && sharedRatio >= 0.8

  return {
    title,
    content: shouldPreviewDelta ? appendedContent : fullContent,
    full_content: fullContent,
    preview_mode: shouldPreviewDelta ? 'delta' : 'full',
    source_action: action,
    selection_context: selectionContext
  }
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
  const chapterTasks = ref([])
  const sessionTasks = ref([])
  const memoryView = ref({})
  const activeArcs = ref([])
  const copilotTab = ref('context')
  const editor = reactive(createEmptyEditorState())
  const requestControllers = new Map()

  const isRequestCanceled = (error) => (
    error?.code === 'ERR_CANCELED'
    || error?.name === 'CanceledError'
    || String(error?.message || '').toLowerCase().includes('canceled')
    || String(error?.message || '').toLowerCase().includes('aborted')
  )

  const createRequestConfig = (key, timeoutMs = 12000) => {
    const requestKey = String(key || '').trim()
    if (requestKey && requestControllers.has(requestKey)) {
      requestControllers.get(requestKey)?.abort?.()
    }
    const controller = new AbortController()
    const timer = setTimeout(() => {
      controller.abort(`timeout:${requestKey}`)
    }, Math.max(1000, Number(timeoutMs || 0)))

    if (requestKey) {
      requestControllers.set(requestKey, controller)
    }

    const finalize = () => {
      clearTimeout(timer)
      if (requestKey && requestControllers.get(requestKey) === controller) {
        requestControllers.delete(requestKey)
      }
    }

    return {
      signal: controller.signal,
      timeout: Math.max(1000, Number(timeoutMs || 0)),
      __finalize: finalize
    }
  }

  const cancelPendingRequests = () => {
    Array.from(requestControllers.values()).forEach((controller) => {
      controller?.abort?.('workspace-cancel')
    })
    requestControllers.clear()
  }

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

  const updateEditorResultState = (patch = {}) => {
    editor.resultState = {
      ...createEmptyEditorState().resultState,
      ...(editor.resultState || {}),
      ...patch
    }
  }

  const upsertSessionTask = (task) => {
    if (!task?.id) return
    const nextTask = { ...task }
    const index = sessionTasks.value.findIndex((item) => item.id === nextTask.id)
    if (index === -1) {
      sessionTasks.value = [nextTask, ...sessionTasks.value].slice(0, 20)
      return
    }
    const previous = sessionTasks.value[index]
    sessionTasks.value.splice(index, 1, { ...previous, ...nextTask })
  }

  const taskCenter = computed(() => buildWorkspaceTaskCenter({
    organizeProgress: organizeProgress.value,
    chapterTasks: chapterTasks.value,
    sessionTasks: sessionTasks.value,
    currentTask: useWorkspaceStore().currentTask,
    chapters: chapters.value
  }))

  const loadStructure = async ({ silent = true } = {}) => {
    if (!projectId.value) {
      memoryView.value = {}
      activeArcs.value = []
      return
    }

    structureLoading.value = true
    const memoryConfig = createRequestConfig(`memory-view:${projectId.value}`, 10000)
    const arcsConfig = createRequestConfig(`active-arcs:${projectId.value}`, 10000)
    try {
      const [nextMemoryView, arcResult] = await Promise.all([
        projectApi.memoryViewV2(projectId.value, memoryConfig).catch((error) => {
          if (!isRequestCanceled(error) && !silent) throw error
          return {}
        }),
        projectApi.activePlotArcsV2(projectId.value, arcsConfig).catch((error) => {
          if (!isRequestCanceled(error) && !silent) throw error
          return {}
        })
      ])
      memoryView.value = nextMemoryView || {}
      activeArcs.value = arcResult?.plot_arcs || []
    } catch (error) {
      if (!isRequestCanceled(error)) {
        errorMessage.value = error?.message || '结构数据加载失败。'
      }
    } finally {
      memoryConfig.__finalize?.()
      arcsConfig.__finalize?.()
      structureLoading.value = false
    }
  }

  const loadBase = async (novelId) => {
    loading.value = true
    errorMessage.value = ''
    const nextNovelConfig = createRequestConfig(`novel:${novelId}`, 8000)
    const chaptersConfig = createRequestConfig(`novel-chapters:${novelId}`, 8000)
    const projectConfig = createRequestConfig(`novel-project:${novelId}`, 8000)
    const progressConfig = createRequestConfig(`novel-progress:${novelId}`, 8000)
    try {
      const [nextNovel, nextChapters, nextProject, nextProgress] = await Promise.all([
        novelApi.get(novelId, nextNovelConfig),
        novelApi.listChapters(novelId, chaptersConfig),
        projectApi.getByNovel(novelId, projectConfig).catch(() => null),
        contentApi.organizeProgress(novelId, progressConfig).catch(() => ({}))
      ])

      novel.value = nextNovel
      chapters.value = nextChapters || []
      project.value = nextProject
      projectId.value = nextProject?.id || ''
      organizeProgress.value = nextProgress || {}

      // Keep first-screen responsive: heavy data is loaded in background.
      if (projectId.value) {
        const tasksConfig = createRequestConfig(`chapter-tasks:${projectId.value}`, 12000)
        void projectApi.chapterTasksV2(projectId.value, tasksConfig)
          .then((tasks) => {
            chapterTasks.value = tasks || []
          })
          .catch((error) => {
            if (!isRequestCanceled(error)) {
              chapterTasks.value = []
            }
          })
          .finally(() => {
            tasksConfig.__finalize?.()
          })
      } else {
        chapterTasks.value = []
      }
      void loadStructure({ silent: true })
    } catch (error) {
      if (!isRequestCanceled(error)) {
        errorMessage.value = error?.message || '加载新工作区失败。'
      }
    } finally {
      nextNovelConfig.__finalize?.()
      chaptersConfig.__finalize?.()
      projectConfig.__finalize?.()
      progressConfig.__finalize?.()
      loading.value = false
    }
  }

  const loadEditorChapter = async (chapterId) => {
    if (!chapterId) {
      resetEditor()
      return
    }

    editor.loading = true
    const chapterConfig = createRequestConfig(`chapter:${chapterId}`, 10000)
    const outlineConfig = createRequestConfig(`chapter-outline:${chapterId}`, 10000)
    const contextConfig = createRequestConfig(`chapter-context:${chapterId}`, 10000)
    try {
      const [chapter, nextOutline, nextContext] = await Promise.all([
        chapterEditorApi.get(chapterId, chapterConfig),
        chapterEditorApi.getOutline(chapterId, outlineConfig).catch(() => ({})),
        chapterEditorApi.getContext(chapterId, contextConfig).catch(() => ({}))
      ])

      let nextTask = nextContext?.chapter_task_seed || {}
      let nextArcs = []
      if (projectId.value) {
        const tasksConfig = createRequestConfig(`chapter-tasks:${projectId.value}`, 10000)
        const arcsConfig = createRequestConfig(`chapter-arcs:${chapterId}`, 10000)
        const [tasks, arcBindings] = await Promise.all([
          projectApi.chapterTasksV2(projectId.value, tasksConfig).catch(() => []),
          projectApi.chapterArcsV2(chapterId, arcsConfig).catch(() => ({}))
        ])
        tasksConfig.__finalize?.()
        arcsConfig.__finalize?.()

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
      updateEditorResultState({
        latestTaskId: '',
        latestAction: '',
        latestResultType: 'none',
        latestDraftType: '',
        lastDecision: 'idle',
        lastUpdatedAt: '',
        latestIssueCount: Array.isArray(editor.integrityCheck?.issue_list) ? editor.integrityCheck.issue_list.length : 0,
        lastError: ''
      })
      editor.activeDraftTab = editor.detemplatedDraft ? 'detemplated' : 'structural'
      editor.dirty = false
    } catch (error) {
      if (!isRequestCanceled(error)) {
        errorMessage.value = error?.message || '章节加载失败。'
      }
    } finally {
      chapterConfig.__finalize?.()
      outlineConfig.__finalize?.()
      contextConfig.__finalize?.()
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

  const buildEditorPayload = (overrides = {}) => ({
    title: editor.chapter.title,
    content: overrides.contentOverride ?? editor.chapter.content,
    outline: editor.outline,
    global_memory_summary: editor.contextMeta.last_chapter_tail || '',
    global_outline_summary: editor.contextMeta.chapter_outline?.goal || '',
    recent_chapter_summaries: (editor.contextMeta.recent_chapter_memories || []).map((item) => (
      item.scene_summary || item.chapter_title || ''
    )),
    ...(overrides.extraRequestData || {})
  })

  const runEditorAiAction = async (action, options = {}) => {
    if (!editor.chapter.id) return null

    const workspaceStore = useWorkspaceStore()
    const selectionContext = options.selectionContext || null
    const selectionLabel = selectionContext?.text ? '选区' : ''
    const taskMetaMap = {
      continue: { type: 'writing', label: `${selectionLabel}AI 续写`.trim(), resultType: 'candidate' },
      optimize: { type: 'rewrite', label: `${selectionLabel}AI 去模板化`.trim(), resultType: 'diff' },
      rewrite: { type: 'rewrite', label: `${selectionLabel}AI 风格改写`.trim(), resultType: 'diff' },
      generate: { type: 'writing', label: `${selectionLabel}根据大纲生成`.trim(), resultType: 'candidate' },
      analyze: { type: 'audit', label: `${selectionLabel}AI 审查`.trim(), resultType: 'issues' }
    }
    const taskMeta = taskMetaMap[action] || { type: action, label: action, resultType: 'none' }
    const taskId = `editor-${action}-${Date.now()}`
    const baseSessionTask = {
      id: taskId,
      type: taskMeta.type,
      task_type: taskMeta.type,
      label: taskMeta.label,
      title: taskMeta.label,
      chapterId: editor.chapter.id,
      chapter_id: editor.chapter.id,
      resultType: taskMeta.resultType,
      started_at: new Date().toISOString()
    }

    editor.aiRunning = true
    updateEditorResultState({
      latestTaskId: taskId,
      latestAction: action,
      latestResultType: taskMeta.resultType,
      latestDraftType: '',
      lastDecision: 'pending',
      lastUpdatedAt: new Date().toISOString(),
      lastError: ''
    })
    upsertSessionTask({
      ...baseSessionTask,
      status: 'running'
    })
    workspaceStore.setCurrentTask({
      id: taskId,
      type: taskMeta.type,
      label: taskMeta.label,
      status: 'running',
      chapterId: editor.chapter.id,
      resultType: taskMeta.resultType
    })
    try {
      const payload = buildEditorPayload({
        contentOverride: options.contentOverride,
        extraRequestData: selectionContext
          ? {
              selection_context: selectionContext,
              selected_text: selectionContext.text || '',
              highlight_range: selectionContext.range || null
            }
          : {}
      })
      let result = null

      if (action === 'continue') {
        result = await chapterEditorApi.continueWrite(editor.chapter.id, payload)
        editor.structuralDraft = buildDraftPayload({
          title: selectionContext?.text ? `${editor.chapter.title || '当前章节'}选区续写稿` : (editor.chapter.title || 'AI 续写稿'),
          action: 'continue',
          currentContent: options.contentOverride ?? editor.chapter.content,
          resultText: result?.result_text || '',
          selectionContext
        })
        editor.activeDraftTab = 'structural'
      } else if (action === 'optimize') {
        result = await chapterEditorApi.optimize(editor.chapter.id, payload)
        editor.detemplatedDraft = {
          ...buildDraftPayload({
            title: selectionContext?.text ? `${editor.chapter.title || '当前章节'}选区去模板化稿` : (editor.chapter.title || 'AI 改写稿'),
            action: 'optimize',
            currentContent: options.contentOverride ?? editor.chapter.content,
            resultText: result?.result_text || '',
            selectionContext
          }),
          display_fallback_to_structural: false
        }
        editor.activeDraftTab = 'detemplated'
      } else if (action === 'rewrite') {
        result = selectionContext?.text
          ? await chapterEditorApi.rewriteSelection(editor.chapter.id, payload)
          : await chapterEditorApi.rewriteStyle(editor.chapter.id, payload)
        editor.detemplatedDraft = {
          ...buildDraftPayload({
            title: selectionContext?.text ? `${editor.chapter.title || '当前章节'}选区改写稿` : (editor.chapter.title || 'AI 改写稿'),
            action: 'rewrite',
            currentContent: options.contentOverride ?? editor.chapter.content,
            resultText: result?.result_text || '',
            selectionContext
          }),
          display_fallback_to_structural: false
        }
        editor.activeDraftTab = 'detemplated'
      } else if (action === 'generate') {
        result = await chapterEditorApi.generateFromOutline(editor.chapter.id, payload)
        editor.structuralDraft = buildDraftPayload({
          title: selectionContext?.text ? `${editor.chapter.title || '当前章节'}选区结构稿` : (editor.chapter.title || 'AI 结构稿'),
          action: 'generate',
          currentContent: options.contentOverride ?? editor.chapter.content,
          resultText: result?.result_text || '',
          selectionContext
        })
        if (result?.outline_draft) {
          editor.outline = { ...editor.outline, ...result.outline_draft }
        }
        editor.activeDraftTab = 'structural'
      } else if (action === 'analyze') {
        result = selectionContext?.text
          ? await chapterEditorApi.analyzeSelection(editor.chapter.id, payload)
          : await chapterEditorApi.analyze(editor.chapter.id, payload)
        editor.activeDraftTab = 'integrity'
      }

      const integrityCheck = buildIntegrityCheckFromResult(result || {})
      if (integrityCheck) {
        editor.integrityCheck = integrityCheck
      }

      updateEditorResultState({
        latestTaskId: taskId,
        latestAction: action,
        latestResultType: taskMeta.resultType,
        latestDraftType: action === 'optimize' || action === 'rewrite'
          ? 'detemplated'
          : (action === 'analyze' ? '' : 'structural'),
        lastDecision: 'pending',
        lastUpdatedAt: new Date().toISOString(),
        latestIssueCount: Array.isArray(editor.integrityCheck?.issue_list) ? editor.integrityCheck.issue_list.length : 0,
        lastError: ''
      })

      upsertSessionTask({
        ...baseSessionTask,
        status: 'completed',
        completed_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        resultType: normalizeWorkspaceTaskResultType({
          ...baseSessionTask,
          resultType: taskMeta.resultType
        })
      })
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
      updateEditorResultState({
        latestTaskId: taskId,
        latestAction: action,
        latestResultType: taskMeta.resultType,
        latestDraftType: '',
        lastDecision: 'error',
        lastUpdatedAt: new Date().toISOString(),
        lastError: error?.message || 'AI 任务失败'
      })
      upsertSessionTask({
        ...baseSessionTask,
        status: 'failed',
        error: error?.message || 'AI 任务失败',
        failed_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
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
      : (draft.full_content || draft.content)
    editor.dirty = true
    updateEditorResultState({
      latestDraftType: type,
      lastDecision: mode === 'append' ? 'applied_append' : 'applied_replace',
      lastUpdatedAt: new Date().toISOString(),
      lastError: ''
    })
    return true
  }

  const saveDraftResult = async ({ type }) => {
    const applied = applyDraftToEditor({ type, mode: 'replace' })
    if (!applied) return false
    await saveEditorChapter()
    updateEditorResultState({
      latestDraftType: type,
      lastDecision: 'saved',
      lastUpdatedAt: new Date().toISOString(),
      lastError: ''
    })
    return true
  }

  const discardDraft = ({ type }) => {
    if (type === 'detemplated') editor.detemplatedDraft = null
    if (type === 'structural') editor.structuralDraft = null
    updateEditorResultState({
      latestDraftType: type,
      lastDecision: 'discarded',
      lastUpdatedAt: new Date().toISOString(),
      lastError: ''
    })
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
    chapterTasks,
    sessionTasks,
    taskCenter,
    memoryView,
    activeArcs,
    copilotTab,
    editor,
    resetEditor,
    syncChapterSnapshot,
    markEditorDirty,
    cancelPendingRequests,
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
