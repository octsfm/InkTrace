import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listAISuggestions = vi.fn()
const getAISuggestion = vi.fn()
const acceptAISuggestion = vi.fn()
const dismissAISuggestion = vi.fn()
const convertAISuggestion = vi.fn()
const applyOutlineAssistSuggestion = vi.fn()
const listConflicts = vi.fn()
const getConflict = vi.fn()

const listAISuggestionsApi = async (request = {}) => {
  const response = await listAISuggestions(request)
  if (!Array.isArray(response?.data?.items)) return response
  const targetId = String(request?.chapter_id || request?.work_id || '')
  const targetKind = request?.chapter_id ? 'chapter_outline' : 'work_outline'
  return {
    ...response,
    data: {
      ...response.data,
      items: response.data.items.map((item) => {
        const payload = item?.payload_json ?? item?.payload ?? {}
        if (payload?.target_kind || payload?.target_id || payload?.chapter_id) return item
        return {
          ...item,
          payload_json: {
            ...payload,
            target_kind: targetKind,
            target_id: targetId,
            chapter_id: request?.chapter_id || undefined,
            target_revision: 3
          }
        }
      })
    }
  }
}

vi.mock('@/api', () => ({
  aiApi: {
    listAISuggestions: listAISuggestionsApi,
    getAISuggestion,
    acceptAISuggestion,
    dismissAISuggestion,
    convertAISuggestion,
    applyOutlineAssistSuggestion,
    listConflicts,
    getConflict
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_outline_assist'
}))

describe('useOutlineAssistStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('loads and clears outline conflict handoff around convert results', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_001',
          title: '正式大纲节点冲突',
          severity: 'blocking',
          summary: '目标节点已被其他操作修改。'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_001',
        summary: '目标节点已被其他操作修改。'
      }
    })

    await store.syncConflictHandoff('conflict_guard:cg_001', {
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(getConflict).toHaveBeenCalledWith('cg_001')
    expect(listConflicts).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.conflictSectionVisible).toBe(true)
    expect(store.conflictLoading).toBe(false)
    expect(store.conflictItems).toHaveLength(1)
    expect(store.conflictDetails.cg_001.summary).toContain('目标节点已被其他操作修改')

    await store.syncConflictHandoff('writing_task:wt_001', {
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(store.conflictSectionVisible).toBe(false)
    expect(store.conflictLoading).toBe(false)
    expect(store.conflictItems).toEqual([])
  })

  it('filters suggestions by mode and guards apply-only states', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    store.setSuggestions([
      {
        suggestion_id: 'sg_polish_001',
        suggestion_type: 'outline_polish',
        status: 'accepted',
        payload_json: {
          target_kind: 'work_outline',
          target_id: 'work-1'
        }
      },
      {
        suggestion_id: 'sg_expand_001',
        suggestion_type: 'outline_expand',
        status: 'accepted',
        payload_json: {
          target_kind: 'selection',
          target_id: null
        }
      },
      {
        suggestion_id: 'sg_detail_001',
        suggestion_type: 'chapter_outline_suggestion',
        status: 'stale',
        payload_json: {
          target_kind: 'work_outline',
          target_id: 'work-1'
        }
      }
    ])

    expect(store.filteredSuggestions.map((item) => item.suggestion_id)).toEqual(['sg_polish_001'])
    expect(store.canApplySuggestion(store.suggestions[0])).toBe(true)
    expect(store.isSelectionOnlySuggestion(store.suggestions[1])).toBe(true)
    expect(store.canApplySuggestion(store.suggestions[1])).toBe(false)

    store.activeMode = 'chapter_outline_detail'

    expect(store.filteredSuggestions.map((item) => item.suggestion_id)).toEqual(['sg_detail_001'])
    expect(store.isStaleSuggestion(store.suggestions[2])).toBe(true)

    store.openApplyConfirm('sg_polish_001')
    expect(store.applyConfirmSuggestionId).toBe('sg_polish_001')

    await store.initializeForWork('work-2')

    expect(store.workId).toBe('work-2')
    expect(store.activeMode).toBe('outline_polish')
    expect(store.suggestions).toEqual([])
    expect(store.applyConfirmSuggestionId).toBe('')
    expect(store.applySubmittingSuggestionId).toBe('')
    expect(store.actionError).toBe('')
  })

  it('exposes consistent action matrix guards for outline and writing-task suggestions', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    const outlineAccepted = {
      suggestion_id: 'sg_outline_accepted',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload_json: {
        target_kind: 'outline_node',
        target_id: 'node_1'
      }
    }
    const writingTaskAccepted = {
      suggestion_id: 'sg_task_accepted',
      suggestion_type: 'writing_task_suggestion',
      status: 'accepted'
    }
    const generatingSuggestion = {
      suggestion_id: 'sg_generating',
      suggestion_type: 'chapter_outline_detail',
      status: 'generating'
    }

    expect(store.canAcceptSuggestion(outlineAccepted)).toBe(false)
    expect(store.canResolveSuggestion(outlineAccepted)).toBe(true)
    expect(store.canConvertSuggestion(outlineAccepted)).toBe(false)
    expect(store.canApplySuggestion(outlineAccepted)).toBe(true)

    expect(store.canAcceptSuggestion(writingTaskAccepted)).toBe(false)
    expect(store.canResolveSuggestion(writingTaskAccepted)).toBe(false)
    expect(store.canConvertSuggestion(writingTaskAccepted)).toBe(true)
    expect(store.canApplySuggestion(writingTaskAccepted)).toBe(false)
    expect(store.isAcceptedWritingTaskSuggestion(writingTaskAccepted)).toBe(true)

    expect(store.canAcceptSuggestion(generatingSuggestion)).toBe(false)
    expect(store.canResolveSuggestion(generatingSuggestion)).toBe(false)
    expect(store.canConvertSuggestion(generatingSuggestion)).toBe(false)
    expect(store.canApplySuggestion(generatingSuggestion)).toBe(false)
  })

  it('loads outline suggestions for current work and chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_task_001',
          suggestion_type: 'writing_task_suggestion',
          status: 'accepted',
          summary: '优化本章写作任务目标'
        }]
      }
    })

    await store.initializeForWork('work-1')
    store.setActiveMode('outline_polish')

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(listAISuggestions).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.suggestions).toHaveLength(1)
    expect(store.activeMode).toBe('writing_task_suggestion')
    expect(store.filteredSuggestions.map((item) => item.suggestion_id)).toEqual(['sg_task_001'])
  })

  it('clears conflict handoff when loading suggestions for another chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_002',
          title: '章节冲突',
          severity: 'blocking',
          summary: 'chapter-1 conflict'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_002',
        summary: 'chapter-1 conflict'
      }
    })
    listAISuggestions.mockResolvedValue({ data: { items: [] } })

    await store.initializeForWork('work-1')
    await store.syncConflictHandoff('conflict_guard:cg_002', {
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(store.conflictSectionVisible).toBe(true)

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    expect(store.conflictSectionVisible).toBe(false)
    expect(store.conflictItems).toEqual([])
    expect(store.conflictDetails).toEqual({})
  })

  it('clears chapter-scoped action state when loading suggestions for another chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listAISuggestions.mockResolvedValue({ data: { items: [] } })

    await store.initializeForWork('work-1')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    store.setActionError('上一章的错误')
    store.openApplyConfirm('sg_apply_001')

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    expect(store.actionError).toBe('')
    expect(store.applyConfirmSuggestionId).toBe('')
    expect(store.applySubmittingSuggestionId).toBe('')
  })

  it('clears suggestion action submitting state when loading suggestions for another chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveAccept

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_submit_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '上一章待采纳建议'
    }])
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))
    listAISuggestions.mockResolvedValue({
      data: {
        items: []
      }
    })

    const acceptPromise = store.acceptSuggestion('sg_submit_001')
    expect(store.submittingSuggestionId).toBe('sg_submit_001')
    expect(store.submittingActionType).toBe('accept')

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    expect(store.submittingSuggestionId).toBe('')
    expect(store.submittingActionType).toBe('')

    resolveAccept({
      data: {
        suggestion_id: 'sg_submit_001',
        status: 'accepted'
      }
    })
    await acceptPromise
  })

  it('ignores stale accept response after chapter context changes', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveAccept

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_repeat_ctx_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: 'chapter-1 suggestion'
    }])
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))
    listAISuggestions.mockResolvedValueOnce({
      data: {
        items: [{
          suggestion_id: 'sg_repeat_ctx_001',
          suggestion_type: 'outline_expand',
          status: 'generated',
          summary: 'chapter-2 suggestion'
        }]
      }
    })

    const acceptPromise = store.acceptSuggestion('sg_repeat_ctx_001')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    expect(store.suggestions[0].summary).toBe('chapter-2 suggestion')
    expect(listAISuggestions).toHaveBeenCalledTimes(1)

    resolveAccept({
      data: {
        suggestion_id: 'sg_repeat_ctx_001',
        status: 'accepted',
        summary: 'late chapter-1 accepted'
      }
    })
    await acceptPromise

    expect(store.suggestions[0].status).toBe('generated')
    expect(store.suggestions[0].summary).toBe('chapter-2 suggestion')
    expect(listAISuggestions).toHaveBeenCalledTimes(1)
  })

  it('does not sync stale conflict handoff after chapter context changes', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveConvert

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_convert_ctx_001',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      summary: 'chapter-1 convert'
    }])
    convertAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveConvert = resolve
    }))
    listAISuggestions.mockResolvedValueOnce({
      data: {
        items: [{
          suggestion_id: 'sg_convert_ctx_001',
          suggestion_type: 'writing_task_suggestion',
          status: 'shown',
          summary: 'chapter-2 suggestion'
        }]
      }
    })

    const convertPromise = store.convertSuggestionWithConflictSync('sg_convert_ctx_001')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    resolveConvert({
      data: {
        suggestion_id: 'sg_convert_ctx_001',
        status: 'converted',
        action: {
          action_payload_ref: 'conflict_guard:cg_ctx_001'
        }
      }
    })
    await convertPromise

    expect(store.conflictSectionVisible).toBe(false)
    expect(store.conflictItems).toEqual([])
    expect(getConflict).not.toHaveBeenCalled()
    expect(listConflicts).not.toHaveBeenCalled()
  })

  it('ignores stale apply response after chapter context changes', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveApply

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_apply_ctx_001',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      summary: 'chapter-1 apply'
    }])
    applyOutlineAssistSuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveApply = resolve
    }))
    listAISuggestions.mockResolvedValueOnce({
      data: {
        items: [{
          suggestion_id: 'sg_apply_ctx_001',
          suggestion_type: 'outline_expand',
          status: 'accepted',
          summary: 'chapter-2 suggestion'
        }]
      }
    })

    const applyPromise = store.applySuggestion('sg_apply_ctx_001')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    resolveApply({
      data: {
        suggestion_id: 'sg_apply_ctx_001',
        status: 'applied',
        summary: 'late applied result'
      }
    })
    await applyPromise

    expect(store.suggestions[0].status).toBe('accepted')
    expect(store.suggestions[0].summary).toBe('chapter-2 suggestion')
    expect(store.applyConfirmSuggestionId).toBe('')
    expect(listAISuggestions).toHaveBeenCalledTimes(1)
  })

  it('ignores stale dismiss response after chapter context changes', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveDismiss

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_dismiss_ctx_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: 'chapter-1 dismiss'
    }])
    dismissAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveDismiss = resolve
    }))
    listAISuggestions.mockResolvedValueOnce({
      data: {
        items: [{
          suggestion_id: 'sg_dismiss_ctx_001',
          suggestion_type: 'outline_expand',
          status: 'generated',
          summary: 'chapter-2 suggestion'
        }]
      }
    })

    const dismissPromise = store.dismissSuggestion('sg_dismiss_ctx_001')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    resolveDismiss({
      data: {
        suggestion_id: 'sg_dismiss_ctx_001',
        status: 'dismissed',
        summary: 'late dismissed result'
      }
    })
    await dismissPromise

    expect(store.suggestions[0].status).toBe('generated')
    expect(store.suggestions[0].summary).toBe('chapter-2 suggestion')
    expect(listAISuggestions).toHaveBeenCalledTimes(1)
  })

  it('ignores stale convert response after chapter context changes', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveConvert

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_convert_state_001',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      summary: 'chapter-1 convert'
    }])
    convertAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveConvert = resolve
    }))
    listAISuggestions.mockResolvedValueOnce({
      data: {
        items: [{
          suggestion_id: 'sg_convert_state_001',
          suggestion_type: 'writing_task_suggestion',
          status: 'shown',
          summary: 'chapter-2 suggestion'
        }]
      }
    })

    const convertPromise = store.convertSuggestion('sg_convert_state_001')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    resolveConvert({
      data: {
        suggestion_id: 'sg_convert_state_001',
        status: 'converted',
        summary: 'late converted result',
        action: {
          action_payload_ref: 'writing_task:wt_001'
        }
      }
    })
    await convertPromise

    expect(store.suggestions[0].status).toBe('shown')
    expect(store.suggestions[0].summary).toBe('chapter-2 suggestion')
    expect(listAISuggestions).toHaveBeenCalledTimes(1)
  })

  it('clears suggestion detail cache when loading suggestions for another chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listAISuggestions.mockResolvedValue({ data: { items: [] } })
    getAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_detail_001',
        summary: '上一章详情'
      }
    })

    await store.initializeForWork('work-1')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })
    await store.loadSuggestionDetail('sg_detail_001')

    expect(store.suggestionDetails.sg_detail_001.summary).toContain('上一章详情')

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })

    expect(store.suggestionDetails).toEqual({})
  })

  it('clears previous chapter suggestions before loading another chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_prev_001',
      suggestion_type: 'outline_expand',
      status: 'pending',
      summary: '上一章建议'
    }])

    listAISuggestions.mockRejectedValueOnce(new Error('network failed'))

    await expect(store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-2'
    })).rejects.toThrow('network failed')

    expect(store.suggestions).toEqual([])
  })

  it('clears stale action error after suggestions reload succeeds for the same chapter', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })
    store.setActionError('旧错误')
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_load_001',
          suggestion_type: 'outline_expand',
          status: 'pending',
          summary: '最新建议'
        }]
      }
    })

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(store.actionError).toBe('')
    expect(store.suggestions[0].suggestion_id).toBe('sg_load_001')
  })

  it('tracks loading state around suggestions requests', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveList

    await store.initializeForWork('work-1')
    listAISuggestions.mockImplementationOnce(() => new Promise((resolve) => {
      resolveList = resolve
    }))

    const loadingPromise = store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(store.loading).toBe(true)

    resolveList({
      data: {
        items: [{
          suggestion_id: 'sg_loading_001',
          suggestion_type: 'outline_expand',
          status: 'pending',
          summary: 'loading finished'
        }]
      }
    })
    await loadingPromise

    expect(store.loading).toBe(false)

    listAISuggestions.mockRejectedValueOnce(new Error('network failed'))
    await expect(store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })).rejects.toThrow('network failed')
    expect(store.loading).toBe(false)
  })

  it('blocks duplicate accept action while suggestion action is submitting', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveAccept

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_accept_pending_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '待采纳建议'
    }])
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_accept_pending_001',
          suggestion_type: 'outline_expand',
          status: 'accepted',
          summary: '采纳后回刷结果'
        }]
      }
    })

    const firstPromise = store.acceptSuggestion('sg_accept_pending_001')
    expect(store.submittingSuggestionId).toBe('sg_accept_pending_001')
    expect(store.submittingActionType).toBe('accept')

    await expect(store.acceptSuggestion('sg_accept_pending_001')).resolves.toBeNull()
    expect(acceptAISuggestion).toHaveBeenCalledTimes(1)

    resolveAccept({
      data: {
        suggestion_id: 'sg_accept_pending_001',
        status: 'accepted'
      }
    })
    await firstPromise

    expect(store.submittingSuggestionId).toBe('')
    expect(store.submittingActionType).toBe('')
  })

  it('blocks sibling actions for the same suggestion while an action is submitting', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    let resolveAccept

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_action_guard_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '待处理建议'
    }])
    acceptAISuggestion.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAccept = resolve
    }))
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_action_guard_001',
          suggestion_type: 'outline_expand',
          status: 'accepted',
          summary: '回刷结果'
        }]
      }
    })

    const firstPromise = store.acceptSuggestion('sg_action_guard_001')
    expect(store.submittingSuggestionId).toBe('sg_action_guard_001')
    expect(store.submittingActionType).toBe('accept')

    await expect(store.dismissSuggestion('sg_action_guard_001')).resolves.toBeNull()
    await expect(store.convertSuggestion('sg_action_guard_001')).resolves.toBeNull()
    expect(dismissAISuggestion).not.toHaveBeenCalled()
    expect(convertAISuggestion).not.toHaveBeenCalled()

    resolveAccept({
      data: {
        suggestion_id: 'sg_action_guard_001',
        status: 'accepted'
      }
    })
    await firstPromise
  })

  it('loads outline suggestion detail into detail cache', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    getAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_detail_001',
        summary: '建议先补侦查，再进入档案室。'
      }
    })

    await store.loadSuggestionDetail('sg_detail_001')

    expect(getAISuggestion).toHaveBeenCalledWith('sg_detail_001')
    expect(store.suggestionDetails.sg_detail_001.summary).toContain('建议先补侦查')
  })

  it('accepts an outline suggestion and syncs local status', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    store.setSuggestions([{
      suggestion_id: 'sg_accept_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '补足潜入前侦查段落'
    }])
    acceptAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_accept_001',
        status: 'accepted'
      }
    })

    await store.acceptSuggestion('sg_accept_001')

    expect(acceptAISuggestion).toHaveBeenCalledWith('sg_accept_001', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(store.suggestions[0].status).toBe('accepted')
  })

  it('refreshes current chapter suggestions after accept and dismiss actions', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_refresh_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '补足潜入前侦查段落'
    }])
    acceptAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_refresh_001',
        status: 'accepted'
      }
    })
    dismissAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_refresh_001',
        status: 'dismissed'
      }
    })
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_001',
            suggestion_type: 'outline_expand',
            status: 'generated',
            summary: 'initial 列表'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_001',
            suggestion_type: 'outline_expand',
            status: 'accepted',
            summary: 'accept 后回刷结果'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_001',
            suggestion_type: 'outline_expand',
            status: 'dismissed',
            summary: 'dismiss 后回刷结果'
          }]
        }
      })

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })
    await store.acceptSuggestion('sg_refresh_001')

    expect(listAISuggestions).toHaveBeenNthCalledWith(2, {
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.suggestions[0].status).toBe('accepted')
    expect(store.suggestions[0].summary).toContain('accept 后回刷结果')

    await store.dismissSuggestion('sg_refresh_001')

    expect(listAISuggestions).toHaveBeenNthCalledWith(3, {
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.suggestions[0].status).toBe('dismissed')
    expect(store.suggestions[0].summary).toContain('dismiss 后回刷结果')
  })

  it('dismisses an outline suggestion and syncs local status', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    store.setSuggestions([{
      suggestion_id: 'sg_dismiss_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '补足潜入前侦查段落'
    }])
    dismissAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_dismiss_001',
        status: 'dismissed'
      }
    })

    await store.dismissSuggestion('sg_dismiss_001')

    expect(dismissAISuggestion).toHaveBeenCalledWith('sg_dismiss_001', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      decision_note: 'manual dismiss'
    }))
    expect(store.suggestions[0].status).toBe('dismissed')
  })

  it('converts a writing-task suggestion and returns its task ref', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    store.setSuggestions([{
      suggestion_id: 'sg_convert_001',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      summary: '补足潜入前侦查段落'
    }])
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_convert_001',
        status: 'converted',
        action: {
          action_payload_ref: 'writing_task:wt_001'
        }
      }
    })

    const result = await store.convertSuggestion('sg_convert_001')

    expect(convertAISuggestion).toHaveBeenCalledWith('sg_convert_001', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(store.suggestions[0].status).toBe('converted')
    expect(result.action.action_payload_ref).toBe('writing_task:wt_001')
    expect(store.pendingWritingTaskId).toBe('wt_001')
  })

  it('keeps conflict handoff closed when writing-task conversion returns a task ref', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    listAISuggestions.mockResolvedValueOnce({ data: { items: [] } })
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })
    store.setSuggestions([{
      suggestion_id: 'sg_convert_flow_001',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      summary: '补足侦查节点'
    }])
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_convert_flow_001',
        status: 'converted',
        action: {
          action_payload_ref: 'writing_task:wt_flow_001'
        }
      }
    })
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_convert_flow_001',
          suggestion_type: 'writing_task_suggestion',
          status: 'converted',
          summary: 'convert 后回刷结果'
        }]
      }
    })
    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_flow_001',
          title: '正式大纲节点冲突',
          severity: 'blocking',
          summary: '目标节点已被其他操作修改。'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_flow_001',
        summary: '目标节点已被其他操作修改。'
      }
    })

    const result = await store.convertSuggestionWithConflictSync('sg_convert_flow_001', {
      workId: 'work-1',
      chapterId: 'chapter-1'
    })

    expect(convertAISuggestion).toHaveBeenCalledWith('sg_convert_flow_001', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(getConflict).not.toHaveBeenCalled()
    expect(listConflicts).not.toHaveBeenCalled()
    expect(result.action.action_payload_ref).toBe('writing_task:wt_flow_001')
    expect(store.conflictSectionVisible).toBe(false)
  })

  it('uses current store work and chapter context for explicit conflict handoff by default', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-9'
    })
    listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg_flow_002',
          title: '正式大纲节点冲突',
          severity: 'blocking',
          summary: '目标节点已被其他操作修改。'
        }]
      }
    })
    getConflict.mockResolvedValue({
      data: {
        record_id: 'cg_flow_002',
        summary: '目标节点已被其他操作修改。'
      }
    })

    await store.syncConflictHandoff('conflict_guard:cg_flow_002')

    expect(listConflicts).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-9'
    })
    expect(getConflict).toHaveBeenCalledWith('cg_flow_002')
  })

  it('refreshes current chapter suggestions after writing-task convert and outline apply actions', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    store.setSuggestions([{
      suggestion_id: 'sg_refresh_002',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      summary: '整理本章写作要点'
    }])
    store.openApplyConfirm('sg_refresh_002')
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_refresh_002',
        status: 'converted',
        action: {
          action_payload_ref: 'writing_task:wt_001'
        }
      }
    })
    applyOutlineAssistSuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_refresh_002',
        status: 'applied',
        success: true
      }
    })
    listAISuggestions
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_002',
            suggestion_type: 'writing_task_suggestion',
            status: 'shown',
            summary: 'initial 列表'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_002',
            suggestion_type: 'writing_task_suggestion',
            status: 'converted',
            summary: 'convert 后回刷结果'
          }]
        }
      })
      .mockResolvedValueOnce({
        data: {
          items: [{
            suggestion_id: 'sg_refresh_002',
            suggestion_type: 'outline_expand',
            status: 'converted',
            summary: 'apply 后回刷结果'
          }]
        }
      })

    await store.loadSuggestions({
      workId: 'work-1',
      chapterId: 'chapter-1'
    })
    await store.convertSuggestion('sg_refresh_002')

    expect(listAISuggestions).toHaveBeenNthCalledWith(2, {
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.suggestions[0].status).toBe('converted')
    expect(store.suggestions[0].summary).toContain('convert 后回刷结果')

    store.setSuggestions([{
      suggestion_id: 'sg_refresh_002',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      summary: '重新进入 apply'
    }])
    store.openApplyConfirm('sg_refresh_002')
    await store.applySuggestion('sg_refresh_002')

    expect(listAISuggestions).toHaveBeenNthCalledWith(3, {
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.suggestions[0].status).toBe('converted')
    expect(store.suggestions[0].summary).toContain('apply 后回刷结果')
  })

  it('applies an accepted outline suggestion and resets confirm state', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    store.setSuggestions([{
      suggestion_id: 'sg_apply_001',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      summary: '补足潜入前侦查段落'
    }])
    store.openApplyConfirm('sg_apply_001')
    applyOutlineAssistSuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_apply_001',
        status: 'applied',
        success: true
      }
    })

    const result = await store.applySuggestion('sg_apply_001')

    expect(applyOutlineAssistSuggestion).toHaveBeenCalledWith('sg_apply_001', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(store.suggestions[0].status).toBe('converted')
    expect(store.applyConfirmSuggestionId).toBe('')
    expect(store.applySubmittingSuggestionId).toBe('')
    expect(result.success).toBe(true)
  })

  it('opens the existing conflict section when outline apply requires conflict review', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listAISuggestions.mockResolvedValueOnce({ data: { items: [] } })
    await store.loadSuggestions({ workId: 'work-1', chapterId: 'chapter-1' })
    store.setSuggestions([{
      suggestion_id: 'sg_apply_conflict_001',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload_json: {
        target_kind: 'chapter_outline',
        target_id: 'chapter-1',
        target_revision: 3
      }
    }])
    const conflictError = Object.assign(new Error('conflict review required'), {
      response: {
        status: 409,
        data: {
          error: {
            error_code: 'P2_OUTLINE_CONFLICT_REVIEW_REQUIRED',
            safe_message: '存在需要人工处理的冲突。',
            retryable: false,
            data: {
              record_refs: ['cg_apply_001']
            }
          }
        }
      }
    })
    applyOutlineAssistSuggestion.mockRejectedValueOnce(conflictError)
    getConflict.mockResolvedValueOnce({
      data: {
        record_id: 'cg_apply_001',
        summary: '目标大纲与已确认设定存在冲突。'
      }
    })
    listConflicts.mockResolvedValueOnce({
      data: {
        items: [{
          record_id: 'cg_apply_001',
          severity: 'blocking',
          summary: '目标大纲与已确认设定存在冲突。'
        }]
      }
    })

    await expect(store.applySuggestion('sg_apply_conflict_001')).rejects.toBe(conflictError)

    expect(getConflict).toHaveBeenCalledWith('cg_apply_001')
    expect(listConflicts).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(store.conflictSectionVisible).toBe(true)
    expect(store.conflictItems[0].record_id).toBe('cg_apply_001')
  })

  it('falls back to current-target blocking conflicts when review-required has no record refs', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    listAISuggestions.mockResolvedValueOnce({ data: { items: [] } })
    await store.loadSuggestions({ workId: 'work-1', chapterId: 'chapter-1' })
    store.setSuggestions([{
      suggestion_id: 'sg_apply_conflict_without_refs',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload_json: {
        target_kind: 'chapter_outline',
        target_id: 'chapter-1',
        target_revision: 3
      }
    }])
    const conflictError = Object.assign(new Error('conflict review required'), {
      response: {
        status: 409,
        data: {
          detail: {
            code: 'P2_OUTLINE_CONFLICT_REVIEW_REQUIRED',
            message: '存在需要人工处理的冲突。'
          }
        }
      }
    })
    applyOutlineAssistSuggestion.mockRejectedValueOnce(conflictError)
    listConflicts.mockResolvedValueOnce({
      data: {
        items: [
          { record_id: 'cg_info_001', severity: 'info', summary: '普通提示。' },
          { record_id: 'cg_blocking_001', severity: 'blocking', summary: '已确认设定冲突。' }
        ]
      }
    })

    await expect(store.applySuggestion('sg_apply_conflict_without_refs')).rejects.toBe(conflictError)

    expect(listConflicts).toHaveBeenCalledWith({
      work_id: 'work-1',
      chapter_id: 'chapter-1'
    })
    expect(getConflict).not.toHaveBeenCalled()
    expect(store.conflictSectionVisible).toBe(true)
    expect(store.conflictItems.map((item) => item.record_id)).toEqual(['cg_blocking_001'])
  })

  it('keeps target version conflicts out of conflict review and asks for refresh and regeneration', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    store.setSuggestions([{
      suggestion_id: 'sg_apply_version_conflict_001',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload_json: {
        target_kind: 'work_outline',
        target_id: 'work-1',
        target_revision: 3
      }
    }])
    const conflictError = Object.assign(new Error('target changed'), {
      response: {
        status: 409,
        data: {
          error: {
            error_code: 'P2_OUTLINE_TARGET_CONFLICT',
            safe_message: '大纲版本已变化。',
            retryable: false,
            data: {
              record_refs: ['conflict_guard:cg_version_001']
            }
          }
        }
      }
    })
    applyOutlineAssistSuggestion.mockRejectedValueOnce(conflictError)

    await expect(store.applySuggestion('sg_apply_version_conflict_001')).rejects.toBe(conflictError)

    expect(store.actionError).toBe('这份大纲刚刚有改动，请刷新后重新生成建议。')
    expect(store.conflictSectionVisible).toBe(false)
    expect(getConflict).not.toHaveBeenCalled()
    expect(listConflicts).not.toHaveBeenCalled()
  })

  it('blocks invalid convert and apply actions before calling api', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    store.setSuggestions([
      {
        suggestion_id: 'sg_task_001',
        suggestion_type: 'outline_expand',
        status: 'generated'
      },
      {
        suggestion_id: 'sg_pending_001',
        suggestion_type: 'outline_expand',
        status: 'pending'
      }
    ])

    await expect(store.convertSuggestion('sg_task_001')).resolves.toBeNull()
    expect(convertAISuggestion).not.toHaveBeenCalled()
    expect(store.actionError).toContain('只有“写作计划”建议')

    store.clearActionError()
    await expect(store.applySuggestion('sg_pending_001')).resolves.toBeNull()
    expect(applyOutlineAssistSuggestion).not.toHaveBeenCalled()
    expect(store.actionError).toContain('请先选择“先留着”')
  })

  it('clears stale action error after successful accept dismiss and convert actions', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()

    await store.initializeForWork('work-1')
    listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg_clear_error_001',
          suggestion_type: 'outline_expand',
          status: 'accepted',
          summary: '回刷后的合法建议'
        }]
      }
    })

    store.setSuggestions([{
      suggestion_id: 'sg_blocked_001',
      suggestion_type: 'outline_expand',
      status: 'generated'
    }])
    await store.convertSuggestion('sg_blocked_001')
    expect(store.actionError).toContain('只有“写作计划”建议')

    store.setSuggestions([{
      suggestion_id: 'sg_clear_error_001',
      suggestion_type: 'outline_expand',
      status: 'generated',
      summary: '合法建议'
    }])
    acceptAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_clear_error_001',
        status: 'accepted'
      }
    })
    await store.acceptSuggestion('sg_clear_error_001')
    expect(store.actionError).toBe('')

    store.setActionError('旧错误')
    dismissAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_clear_error_001',
        status: 'dismissed'
      }
    })
    await store.dismissSuggestion('sg_clear_error_001')
    expect(store.actionError).toBe('')

    store.setActionError('旧错误')
    store.setSuggestions([{
      suggestion_id: 'sg_clear_error_001',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      summary: '合法写作计划建议'
    }])
    convertAISuggestion.mockResolvedValue({
      data: {
        suggestion_id: 'sg_clear_error_001',
        status: 'converted',
        action: {
          action_payload_ref: 'writing_task:wt_001'
        }
      }
    })
    await store.convertSuggestion('sg_clear_error_001')
    expect(store.actionError).toBe('')
  })
})
