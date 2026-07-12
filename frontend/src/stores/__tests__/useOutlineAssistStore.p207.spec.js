import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  polishOutline: vi.fn(),
  expandOutline: vi.fn(),
  generateChapterOutline: vi.fn(),
  suggestWritingTask: vi.fn(),
  getAISuggestion: vi.fn(),
  listAISuggestions: vi.fn(),
  acceptAISuggestion: vi.fn(),
  dismissAISuggestion: vi.fn(),
  convertAISuggestion: vi.fn(),
  confirmWritingTask: vi.fn(),
  getWritingTask: vi.fn(),
  applyOutlineAssistSuggestion: vi.fn(),
  listConflicts: vi.fn(),
  getConflict: vi.fn()
}))

const assetMocks = vi.hoisted(() => ({
  getWorkOutline: vi.fn(),
  getChapterOutline: vi.fn()
}))

vi.mock('@/api', () => ({ aiApi: apiMocks }))
vi.mock('@/api/works', () => ({ v1WritingAssetsApi: assetMocks }))
vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_outline_assist'
}))

const flushAsync = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

describe('useOutlineAssistStore P2-07 author flow', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.useRealTimers()
    setActivePinia(createPinia())
    apiMocks.listAISuggestions.mockResolvedValue({ data: { items: [] } })
  })

  it('loads the chapter outline as an immutable baseline and keeps the editable source separate', async () => {
    assetMocks.getChapterOutline.mockResolvedValue({
      content_text: '主角趁雨夜潜入旧档案馆。',
      version: 7
    })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')

    expect(assetMocks.getChapterOutline).toHaveBeenCalledWith('chapter-1')
    expect(store.targetKind).toBe('chapter_outline')
    expect(store.targetId).toBe('chapter-1')
    expect(store.baselineText).toBe('主角趁雨夜潜入旧档案馆。')
    expect(store.baselineRevision).toBe(7)

    store.setSourceText('只整理这一句')
    expect(store.sourceText).toBe('只整理这一句')
    expect(store.baselineText).toBe('主角趁雨夜潜入旧档案馆。')
  })

  it('does not generate against stale text when loading a different outline fails', async () => {
    assetMocks.getChapterOutline
      .mockResolvedValueOnce({ content_text: '第一章细纲', version: 1 })
      .mockRejectedValueOnce(new Error('offline'))

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    await expect(store.initializeForTarget('work-1', 'chapter-2')).rejects.toThrow('offline')

    expect(store.targetReady).toBe(false)
    expect(store.baselineText).toBe('')
    expect(store.baselineRevision).toBe(0)
    await expect(store.startGeneration('outline_polish')).resolves.toBeNull()
    expect(apiMocks.polishOutline).not.toHaveBeenCalled()
    expect(store.actionError).toContain('重新读取')
  })

  it('loads the work outline when no chapter is selected and disables chapter-only modes', async () => {
    assetMocks.getWorkOutline.mockResolvedValue({ content_text: '全书从失踪案开始。', version: 3 })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', '')

    expect(assetMocks.getWorkOutline).toHaveBeenCalledWith('work-1')
    expect(store.targetKind).toBe('work_outline')
    expect(store.targetId).toBe('work-1')
    expect(store.isModeDisabled('outline_polish')).toBe(false)
    expect(store.isModeDisabled('outline_expand')).toBe(false)
    expect(store.isModeDisabled('chapter_outline_detail')).toBe(true)
    expect(store.isModeDisabled('writing_task_suggestion')).toBe(true)
  })

  it('supports a temporary text target without pretending it is a saved outline', async () => {
    assetMocks.getWorkOutline.mockResolvedValue({ content_text: '整本大纲', version: 3 })
    apiMocks.polishOutline.mockResolvedValue({ suggestion_id: 'sg-selection', status: 'pending' })
    apiMocks.getAISuggestion.mockResolvedValue({
      suggestion_id: 'sg-selection',
      suggestion_type: 'outline_polish',
      status: 'shown',
      payload: {
        target_kind: 'selection',
        target_id: null,
        target_revision: null,
        target_content_text: '临时片段',
        proposed_content_text: '写顺后的临时片段'
      }
    })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', '')
    await store.selectTarget('selection')
    store.setSourceText('临时片段')
    await store.startGeneration('outline_polish')

    expect(apiMocks.polishOutline).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      target_kind: 'selection',
      target_id: null,
      target_revision: null,
      selected_text: '临时片段'
    }))
    expect(store.isModeDisabled('chapter_outline_detail')).toBe(true)
    expect(store.canApplySuggestion({
      suggestion_type: 'outline_polish',
      status: 'accepted',
      payload: { target_kind: 'selection', target_id: null }
    })).toBe(false)
  })

  it.each([
    ['outline_polish', 'polishOutline'],
    ['outline_expand', 'expandOutline'],
    ['chapter_outline_detail', 'generateChapterOutline'],
    ['writing_task_suggestion', 'suggestWritingTask']
  ])('starts %s with the shared protected-target payload', async (mode, apiMethod) => {
    assetMocks.getChapterOutline.mockResolvedValue({ content_text: '旧细纲', version: 5 })
    apiMocks[apiMethod].mockResolvedValue({
      suggestion_id: `sg-${mode}`,
      status: 'pending'
    })
    apiMocks.getAISuggestion.mockResolvedValue({
      suggestion_id: `sg-${mode}`,
      suggestion_type: mode,
      status: 'generated',
      payload: {
        target_content_text: '旧细纲',
        proposed_content_text: '整理后的新细纲'
      }
    })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    await store.startGeneration(mode)

    const request = apiMocks[apiMethod].mock.calls[0][0]
    expect(request).toEqual(expect.objectContaining({
      work_id: 'work-1',
      target_revision: 5,
      caller_type: 'user_action',
      idempotency_key: expect.any(String)
    }))
    if (mode === 'writing_task_suggestion') {
      expect(request).toEqual(expect.objectContaining({ chapter_id: 'chapter-1' }))
      expect(request).not.toHaveProperty('target_kind')
      expect(request).not.toHaveProperty('target_id')
      expect(request).not.toHaveProperty('selected_text')
    } else if (mode === 'chapter_outline_detail') {
      expect(request).toEqual(expect.objectContaining({
        target_kind: 'chapter_outline',
        target_id: 'chapter-1',
        chapter_goal: '旧细纲'
      }))
      expect(request).not.toHaveProperty('selected_text')
    } else {
      expect(request).toEqual(expect.objectContaining({
        target_kind: 'chapter_outline',
        target_id: 'chapter-1',
        selected_text: '旧细纲'
      }))
    }
    expect(apiMocks.getAISuggestion).toHaveBeenCalledWith(`sg-${mode}`)
    expect(store.suggestions[0].status).toBe('generated')
    expect(store.suggestions[0].payload.proposed_content_text).toBe('整理后的新细纲')
    expect(store.generating).toBe(false)
  })

  it('ignores a late polling response after the author switches chapters', async () => {
    let resolveSuggestion
    assetMocks.getChapterOutline
      .mockResolvedValueOnce({ content_text: '第一章旧细纲', version: 1 })
      .mockResolvedValueOnce({ content_text: '第二章旧细纲', version: 2 })
    apiMocks.polishOutline.mockResolvedValue({ suggestion_id: 'sg-late', status: 'pending' })
    apiMocks.getAISuggestion.mockImplementation(() => new Promise((resolve) => {
      resolveSuggestion = resolve
    }))

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    const generation = store.startGeneration('outline_polish')
    await flushAsync()
    await store.initializeForTarget('work-1', 'chapter-2')

    resolveSuggestion({
      suggestion_id: 'sg-late',
      suggestion_type: 'outline_polish',
      status: 'generated',
      payload: { proposed_content_text: '迟到的第一章建议' }
    })
    await generation

    expect(store.chapterId).toBe('chapter-2')
    expect(store.baselineText).toBe('第二章旧细纲')
    expect(store.suggestions).toEqual([])
  })

  it('uses a new idempotency key for each explicit generation after launch succeeds', async () => {
    assetMocks.getChapterOutline.mockResolvedValue({ content_text: '旧细纲', version: 2 })
    apiMocks.polishOutline
      .mockResolvedValueOnce({ suggestion_id: 'sg-first', status: 'pending' })
      .mockResolvedValueOnce({ suggestion_id: 'sg-second', status: 'pending' })
    apiMocks.getAISuggestion
      .mockResolvedValueOnce({
        suggestion_id: 'sg-first',
        suggestion_type: 'outline_polish',
        status: 'generated',
        payload: { target_content_text: '旧细纲', proposed_content_text: '第一次整理' }
      })
      .mockResolvedValueOnce({
        suggestion_id: 'sg-second',
        suggestion_type: 'outline_polish',
        status: 'generated',
        payload: { target_content_text: '旧细纲', proposed_content_text: '第二次整理' }
      })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    await store.startGeneration('outline_polish')
    await store.startGeneration('outline_polish')

    const firstKey = apiMocks.polishOutline.mock.calls[0][0].idempotency_key
    const secondKey = apiMocks.polishOutline.mock.calls[1][0].idempotency_key
    expect(firstKey).not.toBe(secondKey)
  })

  it('reuses the same idempotency key when the launch response is lost', async () => {
    assetMocks.getChapterOutline.mockResolvedValue({ content_text: '旧细纲', version: 2 })
    apiMocks.polishOutline
      .mockRejectedValueOnce(new Error('network failed'))
      .mockResolvedValueOnce({ suggestion_id: 'sg-retried', status: 'pending' })
    apiMocks.getAISuggestion.mockResolvedValue({
      suggestion_id: 'sg-retried',
      suggestion_type: 'outline_polish',
      status: 'generated',
      payload: { target_content_text: '旧细纲', proposed_content_text: '安全重试结果' }
    })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    await expect(store.startGeneration('outline_polish')).rejects.toThrow('network failed')
    await store.startGeneration('outline_polish')

    expect(apiMocks.polishOutline.mock.calls[0][0].idempotency_key)
      .toBe(apiMocks.polishOutline.mock.calls[1][0].idempotency_key)
  })

  it('converts a writing-plan suggestion directly and explains the remaining human confirmation', async () => {
    apiMocks.convertAISuggestion.mockResolvedValue({
      suggestion_id: 'sg-task',
      status: 'converted',
      action: { action_payload_ref: 'writing_task:task-1' }
    })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    store.setSuggestions([{
      suggestion_id: 'sg-task',
      suggestion_type: 'writing_task_suggestion',
      status: 'shown',
      payload: { task_title: '潜入档案馆' }
    }])

    expect(store.canAcceptSuggestion(store.suggestions[0])).toBe(false)
    expect(store.canConvertSuggestion(store.suggestions[0])).toBe(true)
    await store.convertSuggestion('sg-task')

    expect(apiMocks.acceptAISuggestion).not.toHaveBeenCalled()
    expect(apiMocks.convertAISuggestion).toHaveBeenCalledWith('sg-task', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.any(String)
    }))
    expect(store.actionNotice).toContain('还需要确认使用')
    expect(store.actionNotice).toContain('不会写入正文')

    apiMocks.confirmWritingTask.mockResolvedValue({ writing_task_id: 'task-1', status: 'ready' })
    await store.confirmWritingPlan()
    expect(apiMocks.confirmWritingTask).toHaveBeenCalledWith('task-1', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      idempotency_key: expect.any(String)
    }))
    expect(store.pendingWritingTaskId).toBe('')
    expect(store.actionNotice).toContain('已确认使用')
  })

  it('restores a converted writing plan after reload only while its task still awaits confirmation', async () => {
    apiMocks.listAISuggestions.mockResolvedValue({
      data: {
        items: [{
          suggestion_id: 'sg-other-task',
          suggestion_type: 'writing_task_suggestion',
          status: 'converted',
          payload: { chapter_id: 'chapter-2', target_revision: 2 },
          action: { action_payload_ref: 'writing_task:task-other-chapter' }
        }, {
          suggestion_id: 'sg-recover-task',
          suggestion_type: 'writing_task_suggestion',
          status: 'converted',
          payload: { chapter_id: 'chapter-1', target_revision: 3 },
          action: { action_payload_ref: 'writing_task:task-recover' }
        }]
      }
    })
    apiMocks.getWritingTask.mockResolvedValue({ writing_task_id: 'task-recover', status: 'pending' })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.loadSuggestions({ workId: 'work-1', chapterId: 'chapter-1' })
    expect(apiMocks.getWritingTask).toHaveBeenCalledWith('task-recover')
    expect(store.pendingWritingTaskId).toBe('task-recover')

    setActivePinia(createPinia())
    apiMocks.getWritingTask.mockResolvedValue({ writing_task_id: 'task-recover', status: 'ready' })
    const readyStore = useOutlineAssistStore()
    await readyStore.loadSuggestions({ workId: 'work-1', chapterId: 'chapter-1' })
    expect(readyStore.pendingWritingTaskId).toBe('')
  })

  it('filters the all-work suggestion response to the explicitly selected target', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForWork('work-1')
    store.targetKind = 'work_outline'
    store.targetId = 'work-1'
    store.setSuggestions([{
      suggestion_id: 'sg-work',
      suggestion_type: 'outline_polish',
      status: 'shown',
      payload: { target_kind: 'work_outline', target_id: 'work-1' }
    }, {
      suggestion_id: 'sg-chapter',
      suggestion_type: 'outline_polish',
      status: 'shown',
      payload: { target_kind: 'chapter_outline', target_id: 'chapter-1' }
    }])

    expect(store.filteredSuggestions.map((item) => item.suggestion_id)).toEqual(['sg-work'])
  })

  it('copies a temporary-text result and gives a readable fallback when clipboard access fails', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText }
    })
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    store.setSuggestions([{
      suggestion_id: 'sg-copy',
      suggestion_type: 'outline_polish',
      status: 'shown',
      payload: {
        target_kind: 'selection',
        target_id: null,
        target_revision: null,
        proposed_content_text: '整理后的文字'
      }
    }])

    await expect(store.copySuggestionResult('sg-copy')).resolves.toBe(true)
    expect(writeText).toHaveBeenCalledWith('整理后的文字')
    expect(store.actionNotice).toContain('已复制整理结果')

    writeText.mockRejectedValueOnce(new Error('denied'))
    await expect(store.copySuggestionResult('sg-copy')).resolves.toBe(false)
    expect(store.actionError).toContain('手动复制一次')
  })

  it('does not send an empty temporary-text request', async () => {
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForWork('work-1')
    await store.selectTarget('selection')

    await expect(store.startGeneration('outline_polish')).resolves.toBeNull()
    expect(apiMocks.polishOutline).not.toHaveBeenCalled()
    expect(store.actionError).toBe('先写下想整理的文字。')
  })

  it('applies only an accepted outline suggestion with explicit confirmation and target revision', async () => {
    apiMocks.applyOutlineAssistSuggestion.mockResolvedValue({
      success: true,
      suggestion_id: 'sg-outline',
      new_version: 9
    })
    apiMocks.listAISuggestions.mockResolvedValue({ data: { items: [] } })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    store.setSuggestions([{
      suggestion_id: 'sg-outline',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload: { target_revision: 8, proposed_content_text: '新大纲' }
    }])

    await store.applySuggestion('sg-outline')

    expect(apiMocks.applyOutlineAssistSuggestion).toHaveBeenCalledWith('sg-outline', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      confirm_apply: true,
      target_revision: 8,
      idempotency_key: expect.any(String)
    }))
  })

  it('closes confirmation and permanently blocks the old suggestion after the outline changes', async () => {
    assetMocks.getChapterOutline
      .mockResolvedValueOnce({ content_text: '旧细纲', version: 8 })
      .mockResolvedValueOnce({ content_text: '作者刚改过的细纲', version: 9 })
    const conflictError = Object.assign(new Error('target changed'), {
      response: {
        data: {
          error: {
            code: 'P2_OUTLINE_TARGET_CONFLICT',
            safe_message: '这份大纲刚刚有改动。'
          }
        }
      }
    })
    apiMocks.applyOutlineAssistSuggestion.mockRejectedValueOnce(conflictError)

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    store.setSuggestions([{
      suggestion_id: 'sg-stale-apply',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload: {
        target_kind: 'chapter_outline',
        target_id: 'chapter-1',
        target_revision: 8,
        proposed_content_text: '旧建议'
      }
    }])
    store.openApplyConfirm('sg-stale-apply')

    await expect(store.applySuggestion('sg-stale-apply')).rejects.toBe(conflictError)

    const oldSuggestion = store.suggestions[0]
    expect(store.applyConfirmSuggestionId).toBe('')
    expect(store.targetReady).toBe(false)
    expect(store.isStaleSuggestion(oldSuggestion)).toBe(true)
    expect(store.canApplySuggestion(oldSuggestion)).toBe(false)
    expect(store.actionError).toContain('重新生成建议')

    await expect(store.applySuggestion('sg-stale-apply')).resolves.toBeNull()
    expect(apiMocks.applyOutlineAssistSuggestion).toHaveBeenCalledTimes(1)

    await store.reloadTarget()
    expect(store.targetReady).toBe(true)
    expect(store.baselineRevision).toBe(9)
    expect(store.canApplySuggestion(store.suggestions[0])).toBe(false)
  })

  it('closes confirmation and blocks the old suggestion when conflict review is required', async () => {
    assetMocks.getChapterOutline.mockResolvedValue({ content_text: '旧细纲', version: 4 })
    const conflictError = Object.assign(new Error('review required'), {
      response: {
        data: {
          error: {
            code: 'P2_OUTLINE_CONFLICT_REVIEW_REQUIRED',
            data: { record_refs: ['cg-review-1'] }
          }
        }
      }
    })
    apiMocks.applyOutlineAssistSuggestion.mockRejectedValueOnce(conflictError)
    apiMocks.getConflict.mockResolvedValue({
      data: { record_id: 'cg-review-1', summary: '章节安排和已确认计划冲突。' }
    })
    apiMocks.listConflicts.mockResolvedValue({
      data: {
        items: [{
          record_id: 'cg-review-1',
          severity: 'blocking',
          status: 'open',
          summary: '章节安排和已确认计划冲突。'
        }]
      }
    })

    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    await store.initializeForTarget('work-1', 'chapter-1')
    store.setSuggestions([{
      suggestion_id: 'sg-review-apply',
      suggestion_type: 'outline_polish',
      status: 'accepted',
      payload: {
        target_kind: 'chapter_outline',
        target_id: 'chapter-1',
        target_revision: 4,
        proposed_content_text: '待处理冲突的建议'
      }
    }])
    store.openApplyConfirm('sg-review-apply')

    await expect(store.applySuggestion('sg-review-apply')).rejects.toBe(conflictError)

    expect(store.applyConfirmSuggestionId).toBe('')
    expect(store.targetReady).toBe(false)
    expect(store.canApplySuggestion(store.suggestions[0])).toBe(false)
    expect(store.conflictSectionVisible).toBe(true)
    expect(store.conflictItems[0].record_id).toBe('cg-review-1')
    expect(store.actionError).toContain('处理后请刷新并重新生成建议')

    await expect(store.applySuggestion('sg-review-apply')).resolves.toBeNull()
    expect(apiMocks.applyOutlineAssistSuggestion).toHaveBeenCalledTimes(1)
  })

  it('still lets the author discard an accepted outline suggestion', async () => {
    apiMocks.dismissAISuggestion.mockResolvedValue({
      suggestion_id: 'sg-accepted-dismiss',
      suggestion_type: 'outline_expand',
      status: 'dismissed'
    })
    const { useOutlineAssistStore } = await import('../useOutlineAssistStore')
    const store = useOutlineAssistStore()
    store.setSuggestions([{
      suggestion_id: 'sg-accepted-dismiss',
      suggestion_type: 'outline_expand',
      status: 'accepted',
      payload: { target_kind: 'work_outline', target_id: 'work-1', target_revision: 2 }
    }])

    expect(store.canResolveSuggestion(store.suggestions[0])).toBe(true)
    await store.dismissSuggestion('sg-accepted-dismiss')
    expect(apiMocks.dismissAISuggestion).toHaveBeenCalledWith(
      'sg-accepted-dismiss',
      expect.objectContaining({ caller_type: 'user_action', user_action: true })
    )
    expect(store.suggestions[0].status).toBe('dismissed')
  })
})
