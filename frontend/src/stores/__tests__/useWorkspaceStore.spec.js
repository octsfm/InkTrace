import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useWorkspaceStore } from '../useWorkspaceStore'

describe('useWorkspaceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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
})
