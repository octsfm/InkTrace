import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const createSelectionRewrite = vi.fn()
const getSelectionRewrite = vi.fn()
const applySelectionRewrite = vi.fn()
const rejectSelectionRewrite = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    createSelectionRewrite,
    getSelectionRewrite,
    applySelectionRewrite,
    rejectSelectionRewrite
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_selection_rewrite'
}))

describe('useSelectionRewriteStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('creates rewrite request with current selection and keeps generating state', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    createSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'generating'
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

    const result = await store.createRewrite('polish')

    expect(createSelectionRewrite).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      chapter_id: 'chapter-1',
      chapter_revision: 7,
      draft_revision: 12,
      source_text: '月光落在窗台上',
      start_pos: 4,
      end_pos: 12,
      mode: 'polish'
    }))
    expect(createSelectionRewrite.mock.calls[0][0].source_hash).toMatch(/^[a-f0-9]{64}$/)
    expect(result).toMatchObject({
      rewrite_id: 'srw_001',
      status: 'generating'
    })
    expect(store.activeRewriteId).toBe('srw_001')
    expect(store.status).toBe('generating')
  })

  it('loads pending rewrite result and opens diff modal for editing', async () => {
    const { useSelectionRewriteStore } = await import('../useSelectionRewriteStore')
    const store = useSelectionRewriteStore()

    getSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'pending',
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
    expect(store.modalVisible).toBe(true)
    expect(store.editedText).toBe('月光静静落在旧窗台上')
    expect(store.diffSummary).toBe('补强环境描写')
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
      rewritten_text: '月光静静落在旧窗台上'
    }
    store.activeRewriteId = 'srw_001'
    store.editedText = '月光静静落在旧窗台上'

    const result = await store.applyCurrentRewrite()

    expect(applySelectionRewrite).toHaveBeenCalledWith('srw_001', {
      final_text: '月光静静落在旧窗台上',
      chapter_revision: 7,
      draft_revision: 12,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: expect.stringMatching(/^selection_rewrite_apply_/)
    })
    expect(result.status).toBe('applied')
    expect(chapterStore.activeChapterContent).toBe('这是旧文本，月光静静落在旧窗台上，风吹进来。')
    expect(store.modalVisible).toBe(false)
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
