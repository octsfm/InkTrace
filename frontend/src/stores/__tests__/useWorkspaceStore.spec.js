import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '../useWorkspaceStore'

const mockGetWork = vi.fn()
const mockGetSession = vi.fn()
const mockSaveSession = vi.fn()
const mockUpdateChapter = vi.fn()

vi.mock('@/api', () => ({
  v1WorksApi: {
    get: (...args) => mockGetWork(...args)
  },
  v1SessionsApi: {
    get: (...args) => mockGetSession(...args),
    save: (...args) => mockSaveSession(...args)
  },
  v1ChaptersApi: {
    update: (...args) => mockUpdateChapter(...args)
  }
}))

describe('useWorkspaceStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('initializes work and session from V1 APIs', async () => {
    mockGetWork.mockResolvedValueOnce({
      id: 'work-1',
      title: '作品',
      author: '作者',
      current_word_count: 0
    })
    mockGetSession.mockResolvedValueOnce({
      work_id: 'work-1',
      last_open_chapter_id: 'chapter-2',
      cursor_position: 18,
      scroll_top: 32,
      updated_at: '2026-04-30T00:00:00Z'
    })
    const store = useWorkspaceStore()

    const result = await store.initializeWorkspace('work-1')

    expect(mockGetWork).toHaveBeenCalledWith('work-1')
    expect(mockGetSession).toHaveBeenCalledWith('work-1')
    expect(result.work.title).toBe('作品')
    expect(result.session.last_open_chapter_id).toBe('chapter-2')
    expect(store.work).toEqual(expect.objectContaining({ id: 'work-1' }))
    expect(store.session).toEqual(expect.objectContaining({ work_id: 'work-1' }))
    expect(store.lastOpenChapterId).toBe('chapter-2')
    expect(store.cursorPosition).toBe(18)
    expect(store.scrollTop).toBe(32)
    expect(store.hydrated).toBe(true)
  })

  it('keeps backend fallback session when no previous session exists', async () => {
    mockGetWork.mockResolvedValueOnce({ id: 'work-2', title: '作品', author: '' })
    mockGetSession.mockResolvedValueOnce({
      work_id: 'work-2',
      last_open_chapter_id: 'first-chapter',
      cursor_position: 0,
      scroll_top: 0,
      updated_at: '2026-04-30T00:00:00Z'
    })
    const store = useWorkspaceStore()

    await store.initializeWorkspace('work-2')

    expect(store.lastOpenChapterId).toBe('first-chapter')
    expect(store.cursorPosition).toBe(0)
    expect(store.scrollTop).toBe(0)
    expect(store.hydrated).toBe(true)
  })

  it('saves session position without calling chapter save API', async () => {
    mockSaveSession.mockResolvedValueOnce({
      work_id: 'work-3',
      last_open_chapter_id: 'chapter-9',
      cursor_position: 44,
      scroll_top: 88,
      updated_at: '2026-04-30T00:01:00Z'
    })
    const store = useWorkspaceStore()
    store.setWorkContext('work-3')

    const saved = await store.saveSessionPosition({
      activeChapterId: 'chapter-9',
      cursorPosition: 44,
      scrollTop: 88
    })

    expect(mockSaveSession).toHaveBeenCalledWith('work-3', {
      active_chapter_id: 'chapter-9',
      cursor_position: 44,
      scroll_top: 88
    })
    expect(mockUpdateChapter).not.toHaveBeenCalled()
    expect(saved.last_open_chapter_id).toBe('chapter-9')
    expect(store.sessionUpdatedAt).toBe('2026-04-30T00:01:00Z')
  })

  it('hydrates session payload into workspace state', () => {
    const store = useWorkspaceStore()
    store.setWorkContext('work-1')
    store.hydrateSession({
      last_open_chapter_id: 'chapter-2',
      cursor_position: 18,
      scroll_top: 32,
      updated_at: '2026-04-28T14:00:00.000Z'
    })

    expect(store.workId).toBe('work-1')
    expect(store.lastOpenChapterId).toBe('chapter-2')
    expect(store.cursorPosition).toBe(18)
    expect(store.scrollTop).toBe(32)
    expect(store.hydrated).toBe(true)
    expect(store.sessionUpdatedAt).toBe('2026-04-28T14:00:00.000Z')
    expect(store.getViewport('chapter-2')).toEqual({
      cursorPosition: 18,
      scrollTop: 32
    })
  })

  it('builds session payload from current viewport', () => {
    const store = useWorkspaceStore()
    store.setWorkContext('work-2')
    store.captureViewport({
      chapterId: 'chapter-5',
      cursorPosition: 99,
      scrollTop: 128
    })

    expect(store.toSessionPayload()).toEqual({
      chapter_id: 'chapter-5',
      cursor_position: 99,
      scroll_top: 128
    })
  })

  it('tracks per-chapter viewport cache', () => {
    const store = useWorkspaceStore()
    store.setWorkContext('work-3')
    store.captureViewport({
      chapterId: 'chapter-1',
      cursorPosition: 12,
      scrollTop: 48
    })
    store.captureViewport({
      chapterId: 'chapter-2',
      cursorPosition: 27,
      scrollTop: 96
    })

    expect(store.getViewport('chapter-1')).toEqual({
      cursorPosition: 12,
      scrollTop: 48
    })
    expect(store.getViewport('chapter-2')).toEqual({
      cursorPosition: 27,
      scrollTop: 96
    })
  })

  it('normalizes fractional viewport values before persisting session payload', () => {
    const store = useWorkspaceStore()
    store.setWorkContext('work-4')
    store.captureViewport({
      chapterId: 'chapter-9',
      cursorPosition: 18.4,
      scrollTop: 96.6
    })

    expect(store.cursorPosition).toBe(18)
    expect(store.scrollTop).toBe(97)
    expect(store.getViewport('chapter-9')).toEqual({
      cursorPosition: 18,
      scrollTop: 97
    })
    expect(store.toSessionPayload()).toEqual({
      chapter_id: 'chapter-9',
      cursor_position: 18,
      scroll_top: 97
    })
  })
})
