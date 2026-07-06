import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const createSelectionRewrite = vi.fn()
const getSelectionRewrite = vi.fn()
const applySelectionRewrite = vi.fn()
const rejectSelectionRewrite = vi.fn()
const listSelectionRewriteHistory = vi.fn()
const clearSelectionRewriteHistory = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    createSelectionRewrite,
    getSelectionRewrite,
    applySelectionRewrite,
    rejectSelectionRewrite,
    listSelectionRewriteHistory,
    clearSelectionRewriteHistory
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_selection_rewrite'
}))

describe('useSelectionRewriteStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('creates rewrite request with current selection and records generating rewrite id', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()

    createSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'generating',
        request_id: 'job_001'
      }
    })

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: '夜色沉沉，月光落在窗台上，窗外传来风声。',
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', '夜色沉沉，月光落在窗台上，窗外传来风声。')

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.setSelection({
      text: '月光落在窗台上',
      start: 4,
      end: 12
    })

    const result = await store.createRewrite('polish')

    expect(createSelectionRewrite).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      chapter_revision: 7,
      draft_revision: 12,
      draft_text_hash: expect.stringMatching(/^[a-f0-9]{64}$/),
      draft_length: 20,
      source_text: '月光落在窗台上',
      start_pos: 4,
      end_pos: 12,
      context_before: '夜色沉沉',
      context_after: '，窗外传来风声。',
      mode: 'polish'
    }))
    expect(createSelectionRewrite.mock.calls[0][0].source_hash).toMatch(/^[a-f0-9]{64}$/)
    expect(result).toMatchObject({
      rewrite_id: 'srw_001',
      status: 'generating',
      request_id: 'job_001'
    })
    expect(store.activeRewriteId).toBe('srw_001')
    expect(store.requestId).toBe('job_001')
    expect(store.status === 'generating' || store.status === '').toBe(true)
  })

  it('caps selection rewrite prompt context to 500 chars on each side', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()
    const longBefore = '前'.repeat(620)
    const selected = '月光落在窗台上'
    const longAfter = '后'.repeat(620)

    createSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'generating',
        request_id: 'job_001'
      }
    })

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: `${longBefore}${selected}${longAfter}`,
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', `${longBefore}${selected}${longAfter}`)

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.setSelection({
      text: selected,
      start: longBefore.length,
      end: longBefore.length + selected.length
    })

    await store.createRewrite('rewrite')

    expect(createSelectionRewrite).toHaveBeenCalledWith(expect.objectContaining({
      context_before: '前'.repeat(500),
      context_after: '后'.repeat(500)
    }))
  })

  it('loads pending rewrite result and opens diff modal for editing', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    getSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'pending',
        request_id: 'job_001',
        source_start_pos: 4,
        source_end_pos: 12,
        rewritten_text: '月光静静落在旧窗台上',
        diff_summary: '补强环境描写',
        word_count_before: 8,
        word_count_after: 11
      }
    })

    store.activeRewriteId = 'srw_001'
    const result = await store.loadRewriteResult('srw_001')

    expect(getSelectionRewrite).toHaveBeenCalledWith('srw_001')
    expect(result.status).toBe('pending')
    expect(store.requestId).toBe('job_001')
    expect(store.modalVisible).toBe(true)
    expect(store.editedText).toBe('月光静静落在旧窗台上')
    expect(store.diffSummary).toBe('补强环境描写')
  })

  it('polls generating rewrite result until pending and opens diff modal automatically', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    createSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'generating'
      }
    })
    getSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'pending',
        source_start_pos: 4,
        source_end_pos: 12,
        rewritten_text: '月光静静落在旧窗台上',
        diff_summary: '补强环境描写'
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.setSelection({
      text: '月光落在窗台上',
      start: 4,
      end: 12
    })

    const pendingPromise = store.createRewrite('polish')
    await vi.runAllTimersAsync()
    await Promise.resolve()
    await nextTick()
    await Promise.resolve()
    const created = await pendingPromise

    expect(created.status).toBe('generating')
    expect(getSelectionRewrite).toHaveBeenCalledWith('srw_001')
    expect(store.status).toBe('pending')
    expect(store.modalVisible).toBe(true)
    expect(store.editedText).toBe('月光静静落在旧窗台上')
  })

  it('keeps request id when the first polling response omits it', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    createSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'generating',
        request_id: 'job_001'
      }
    })
    getSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'pending',
        source_start_pos: 4,
        source_end_pos: 12,
        rewritten_text: '月光静静落在旧窗台上',
        diff_summary: '补强环境描写'
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.setSelection({
      text: '月光落在窗台上',
      start: 4,
      end: 12
    })

    await store.createRewrite('polish')
    await vi.runAllTimersAsync()
    await Promise.resolve()
    await nextTick()

    expect(store.requestId).toBe('job_001')
    expect(store.status).toBe('pending')
  })

  it('stores terminal failed rewrite message and stops polling', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    getSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'failed',
        error_code: 'output_schema_invalid',
        error_message: '选区改写生成失败，请稍后重试。'
      }
    })

    store.activeRewriteId = 'srw_001'
    store.pollingTimerId = 123

    const result = await store.loadRewriteResult('srw_001')

    expect(result.status).toBe('failed')
    expect(store.status).toBe('failed')
    expect(store.actionError).toBe('选区改写生成失败，请稍后重试。')
    expect(store.pollingTimerId).toBe(null)
    expect(store.modalVisible).toBe(false)
  })

  it('uses design-aligned conflicted message for terminal rewrite result', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    getSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'conflicted'
      }
    })

    store.activeRewriteId = 'srw_001'
    const result = await store.loadRewriteResult('srw_001')

    expect(result.status).toBe('conflicted')
    expect(store.actionError).toBe('原文已变化，请重新选择。')
  })

  it('applies returned patch to current chapter draft through chapter store only', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: '这是旧文本，月光落在窗台上，风吹进来。',
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', '这是旧文本，月光落在窗台上，风吹进来。')

    applySelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'applied',
        patch: {
          range: [6, 13],
          replacement: '月光静静落在旧窗台上'
        }
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      source_start_pos: 6,
      source_end_pos: 13,
      rewritten_text: '月光静静落在旧窗台上'
    }
    store.activeRewriteId = 'srw_001'
    store.editedText = '月光静静落在旧窗台上'

    const result = await store.applyCurrentRewrite()

    expect(applySelectionRewrite).toHaveBeenCalledWith('srw_001', expect.objectContaining({
      final_text: '月光静静落在旧窗台上',
      chapter_revision: 7,
      draft_revision: 12,
      draft_text_hash: expect.stringMatching(/^[a-f0-9]{64}$/),
      draft_length: 19,
      range_text: '月光落在窗台上',
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.stringMatching(/^selection_rewrite_apply_/)
    }))
    expect(result.status).toBe('applied')
    expect(chapterStore.activeChapterContent).toBe('这是旧文本，月光静静落在旧窗台上，风吹进来。')
    expect(store.modalVisible).toBe(false)
  })

  it('keeps draft unchanged and exposes manual retry error when local patch apply fails', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: '这是旧文本，月光落在窗台上，风吹进来。',
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', '这是旧文本，月光已不在窗台上，风吹进来。')

    applySelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'applied',
        patch: {
          range: [6, 13],
          replacement: '月光静静落在旧窗台上'
        }
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      source_start_pos: 6,
      source_end_pos: 13,
      source_text: '月光落在窗台上',
      rewritten_text: '月光静静落在旧窗台上'
    }
    store.activeRewriteId = 'srw_001'
    store.editedText = '月光静静落在旧窗台上'
    store.modalVisible = true

    await expect(store.applyCurrentRewrite()).rejects.toThrow('selection_rewrite_patch_apply_failed')

    expect(chapterStore.activeChapterContent).toBe('这是旧文本，月光已不在窗台上，风吹进来。')
    expect(store.modalVisible).toBe(true)
    expect(store.actionError).toBe('改写结果已确认，但本地草稿应用失败，请手动重试。')
  })

  it('stores undo snapshot after apply and rolls back draft without backend call', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: '这是旧文本，月光落在窗台上，风吹进来。',
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', '这是旧文本，月光落在窗台上，风吹进来。')

    applySelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'applied',
        patch: {
          range: [6, 13],
          replacement: '月光静静落在旧窗台上'
        }
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      source_start_pos: 6,
      source_end_pos: 13,
      rewritten_text: '月光静静落在旧窗台上'
    }
    store.activeRewriteId = 'srw_001'
    store.editedText = '月光静静落在旧窗台上'

    await store.applyCurrentRewrite()

    expect(store.canUndoLastApply).toBe(true)
    expect(chapterStore.activeChapterContent).toBe('这是旧文本，月光静静落在旧窗台上，风吹进来。')

    const restored = store.undoLastApply()

    expect(restored).toBe(true)
    expect(chapterStore.activeChapterContent).toBe('这是旧文本，月光落在窗台上，风吹进来。')
    expect(store.canUndoLastApply).toBe(false)
    expect(applySelectionRewrite).toHaveBeenCalledTimes(1)
  })

  it('expires undo snapshot after 5 seconds', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: '这是旧文本，月光落在窗台上，风吹进来。',
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', '这是旧文本，月光落在窗台上，风吹进来。')

    applySelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'applied',
        patch: {
          range: [6, 13],
          replacement: '月光静静落在旧窗台上'
        }
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      source_start_pos: 6,
      source_end_pos: 13,
      rewritten_text: '月光静静落在旧窗台上'
    }
    store.activeRewriteId = 'srw_001'
    store.editedText = '月光静静落在旧窗台上'

    await store.applyCurrentRewrite()

    expect(store.canUndoLastApply).toBe(true)

    await vi.advanceTimersByTimeAsync(5000)

    expect(store.canUndoLastApply).toBe(false)
    expect(store.undoLastApply()).toBe(false)
    expect(chapterStore.activeChapterContent).toBe('这是旧文本，月光静静落在旧窗台上，风吹进来。')
  })

  it('retries last rewrite with the previous mode', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const { useChapterDataStore } = await import('../useChapterDataStore')
    const store = useSelectionRewriteStore()
    const chapterStore = useChapterDataStore()

    createSelectionRewrite
      .mockResolvedValueOnce({
        data: {
          rewrite_id: 'srw_001',
          status: 'generating',
          request_id: 'job_001'
        }
      })
      .mockResolvedValueOnce({
        data: {
          rewrite_id: 'srw_002',
          status: 'generating',
          request_id: 'job_002'
        }
      })

    chapterStore.setChapters([{
      id: 'chapter-1',
      title: '第一章',
      content: '夜色沉沉，月光落在窗台上，窗外传来风声。',
      version: 7,
      order_index: 1
    }])
    chapterStore.setActiveChapter('chapter-1')
    chapterStore.updateChapterDraft('chapter-1', '夜色沉沉，月光落在窗台上，窗外传来风声。')

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.setSelection({
      text: '月光落在窗台上',
      start: 4,
      end: 12
    })

    await store.createRewrite('polish')
    await store.retryLastRewrite()

    expect(createSelectionRewrite).toHaveBeenCalledTimes(2)
    expect(createSelectionRewrite.mock.calls[1][0].mode).toBe('polish')
    expect(store.requestId).toBe('job_002')
  })

  it('loads chapter history and keeps expired status from backend', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    listSelectionRewriteHistory.mockResolvedValue({
      data: {
        items: [{
          rewrite_id: 'srw_hist_001',
          chapter_id: 'chapter-1',
          status: 'expired',
          rewrite_mode: 'rewrite',
          source_text: '月光落在窗台上'
        }]
      }
    })

    const items = await store.loadChapterHistory('chapter-1')

    expect(listSelectionRewriteHistory).toHaveBeenCalledWith('chapter-1')
    expect(items).toHaveLength(1)
    expect(store.historyItems[0].status).toBe('expired')
  })

  it('clears chapter history and resets current rewrite state', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    clearSelectionRewriteHistory.mockResolvedValue({
      data: {
        chapter_id: 'chapter-1',
        cleared_count: 2
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 7,
      draftRevision: 12
    })
    store.activeRewriteId = 'srw_001'
    store.requestId = 'job_001'
    store.status = 'pending'
    store.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      rewrite_mode: 'rewrite'
    }
    store.historyItems = [{
      rewrite_id: 'srw_hist_001',
      status: 'expired'
    }]

    const result = await store.clearChapterHistory()

    expect(clearSelectionRewriteHistory).toHaveBeenCalledWith('chapter-1')
    expect(result.cleared_count).toBe(2)
    expect(store.activeRewriteId).toBe('')
    expect(store.requestId).toBe('')
    expect(store.status).toBe('')
    expect(store.historyItems).toEqual([])
  })

  it('rejects current rewrite and clears modal state', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    rejectSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'rejected'
      }
    })

    store.activeRewriteId = 'srw_001'
    store.modalVisible = true
    store.editedText = '待清理内容'

    const result = await store.rejectCurrentRewrite()

    expect(rejectSelectionRewrite).toHaveBeenCalledWith('srw_001')
    expect(result.status).toBe('rejected')
    expect(store.modalVisible).toBe(false)
    expect(store.editedText).toBe('')
  })
})
