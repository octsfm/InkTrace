import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useChapterDataStore } from '../chapterData'
import { usePreferenceStore } from '../preference'
import { useSaveStateStore } from '../saveState'
import { useWorkspaceStore } from '../workspace'
import { useWritingAssetStore } from '../writingAsset'

describe('Workbench Stage 0 store shells', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes workspace context without business API calls', () => {
    const store = useWorkspaceStore()

    expect(store.workId).toBe('')
    expect(store.lastOpenChapterId).toBe('')
    expect(store.cursorPosition).toBe(0)
    expect(store.scrollTop).toBe(0)
    expect(store.hydrated).toBe(false)
  })

  it('initializes chapter data shell', () => {
    const store = useChapterDataStore()

    expect(store.chapters).toEqual([])
    expect(store.activeChapterId).toBe('')
    expect(store.draftTitle).toBe('')
    expect(store.draftContent).toBe('')
  })

  it('initializes save state shell', () => {
    const store = useSaveStateStore()

    expect(store.status).toBe('idle')
    expect(store.pendingQueue).toEqual([])
    expect(store.conflictPayload).toBeNull()
    expect(store.offline).toBe(false)
  })

  it('initializes writing asset shell', () => {
    const store = useWritingAssetStore()

    expect(store.activeDrawer).toBe('')
    expect(store.assets.timeline).toEqual([])
    expect(store.assetDrafts).toEqual({})
    expect(store.dirtyAssetKeys).toEqual([])
  })

  it('initializes preference shell', () => {
    const store = usePreferenceStore()

    expect(store.focusMode).toBe(false)
    expect(store.fontFamily).toBe('system-ui')
    expect(store.fontSize).toBe(18)
    expect(store.lineHeight).toBe(1.8)
    expect(store.theme).toBe('light')
    expect(store.todayWordDelta).toBe(0)
    expect(store.todayKey).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
