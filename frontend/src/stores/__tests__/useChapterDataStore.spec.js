import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useChapterDataStore } from '../useChapterDataStore'

describe('useChapterDataStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads chapters sorted by order_index without trusting input order', () => {
    const store = useChapterDataStore()

    store.setChapters([
      { id: 'chapter-2', title: '第二章', content: '二', order_index: 2 },
      { id: 'chapter-1', title: '第一章', content: '一', order_index: 1 }
    ])

    expect(store.chapters.map((item) => item.id)).toEqual(['chapter-1', 'chapter-2'])
    expect(store.chapters.map((item) => item.order_index)).toEqual([1, 2])
  })

  it('tracks active chapter and independent title/content drafts', () => {
    const store = useChapterDataStore()
    store.setChapters([{ id: 'chapter-1', title: '远端标题', content: '远端正文', order_index: 1 }])
    store.setActiveChapter('chapter-1')

    store.updateChapterDraft('chapter-1', '本地正文')
    store.updateChapterTitleDraft('chapter-1', '本地标题')

    expect(store.activeChapterContent).toBe('本地正文')
    expect(store.activeChapterTitle).toBe('本地标题')

    store.clearChapterDraft('chapter-1')
    store.clearChapterTitleDraft('chapter-1')

    expect(store.activeChapterContent).toBe('远端正文')
    expect(store.activeChapterTitle).toBe('远端标题')
  })

  it('appends a created chapter, activates it and indicates search should clear', () => {
    const store = useChapterDataStore()
    store.setChapters([{ id: 'chapter-1', title: '', content: '', order_index: 1 }])

    const result = store.appendCreatedChapter(
      { id: 'chapter-2', title: '', content: '', version: 1 },
      { clearSearch: true }
    )

    expect(store.chapters.map((item) => item.id)).toEqual(['chapter-1', 'chapter-2'])
    expect(store.chapters[1].order_index).toBe(2)
    expect(store.activeChapterId).toBe('chapter-2')
    expect(result).toEqual({ activeChapterId: 'chapter-2', clearSearch: true })
  })

  it('removes chapter drafts and keeps local order_index continuous after delete', () => {
    const store = useChapterDataStore()
    store.setChapters([
      { id: 'chapter-1', title: '一', content: '一', order_index: 1 },
      { id: 'chapter-2', title: '二', content: '二', order_index: 2 },
      { id: 'chapter-3', title: '三', content: '三', order_index: 3 }
    ])
    store.setActiveChapter('chapter-2')
    store.updateChapterDraft('chapter-2', '草稿')
    store.updateChapterTitleDraft('chapter-2', '标题草稿')

    store.removeChapter('chapter-2', 'chapter-3')

    expect(store.activeChapterId).toBe('chapter-3')
    expect(store.chapters.map((item) => item.id)).toEqual(['chapter-1', 'chapter-3'])
    expect(store.chapters.map((item) => item.order_index)).toEqual([1, 2])
    expect(store.draftByChapterId).toEqual({})
    expect(store.draftTitleByChapterId).toEqual({})
  })

  it('filters chapters without changing the original chapter order', () => {
    const store = useChapterDataStore()
    store.setChapters([
      { id: 'chapter-1', title: '风起', content: '', order_index: 1 },
      { id: 'chapter-2', title: '雨落', content: '', order_index: 2 },
      { id: 'chapter-3', title: '风停', content: '', order_index: 3 }
    ])

    const filtered = store.getFilteredChapters('风')

    expect(filtered.map((item) => item.id)).toEqual(['chapter-1', 'chapter-3'])
    expect(store.chapters.map((item) => item.id)).toEqual(['chapter-1', 'chapter-2', 'chapter-3'])
  })
})
