import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { localCache } from '@/utils/localCache'
import { useSaveStateStore } from '../useSaveStateStore'

const mockUpdateChapter = vi.fn()

vi.mock('@/api', () => ({
  v1ChaptersApi: {
    update: (...args) => mockUpdateChapter(...args)
  }
}))

describe('useSaveStateStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localCache.clear()
    mockUpdateChapter.mockReset()
  })

  it('initializes save state runtime fields', () => {
    const store = useSaveStateStore()

    expect(store.saveStatus).toBe('synced')
    expect(store.pendingQueue).toEqual([])
    expect(store.retryCount).toBe(0)
    expect(store.nextRetryAt).toBe('')
    expect(store.conflictPayload).toBeNull()
    expect(store.hasConflict).toBe(false)
  })

  it('marks and clears conflict payload inside save state store', () => {
    const store = useSaveStateStore()
    const payload = {
      chapterId: 'ch-2',
      title: 'conflict-title',
      content: 'local-draft'
    }

    store.markConflict(payload, 'version_conflict')

    expect(store.saveStatus).toBe('conflict')
    expect(store.lastError).toBe('version_conflict')
    expect(store.hasConflict).toBe(true)
    expect(store.conflictPayload).toEqual(payload)

    store.clearConflict()

    expect(store.hasConflict).toBe(false)
    expect(store.conflictPayload).toBeNull()
    expect(store.saveStatus).toBe('synced')
  })

  it('deduplicates drafts by chapter and replays them in timestamp order', async () => {
    const store = useSaveStateStore()
    const replayed = []

    store.replaceQueue([
      { chapterId: 'ch-2', content: 'later-old', timestamp: 20 },
      { chapterId: 'ch-1', content: 'earlier', timestamp: 10 },
      { chapterId: 'ch-2', content: 'latest', timestamp: 30 }
    ])

    expect(store.pendingQueue).toEqual([
      {
        workId: '',
        chapterId: 'ch-1',
        title: '',
        content: 'earlier',
        version: 1,
        cursorPosition: 0,
        scrollTop: 0,
        timestamp: 10
      },
      {
        workId: '',
        chapterId: 'ch-2',
        title: '',
        content: 'latest',
        version: 1,
        cursorPosition: 0,
        scrollTop: 0,
        timestamp: 30
      }
    ])

    const result = await store.replayOfflineDrafts({
      replay: async (draft) => {
        replayed.push(draft.chapterId)
      }
    })

    expect(replayed).toEqual(['ch-1', 'ch-2'])
    expect(result).toEqual({
      successCount: 2,
      remainingDrafts: []
    })
    expect(store.pendingQueue).toEqual([])
  })

  it('writes input drafts to local cache immediately', () => {
    const store = useSaveStateStore()

    const draft = store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: 'chapter-title',
      content: 'local-first-draft',
      version: 2,
      timestamp: 100
    })

    expect(draft).toMatchObject({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: 'chapter-title',
      content: 'local-first-draft',
      version: 2,
      timestamp: 100
    })
    expect(store.readLocalDraft({ workId: 'work-1', chapterId: 'ch-1' })).toMatchObject({
      content: 'local-first-draft'
    })
    expect(store.pendingQueue).toHaveLength(1)
  })

  it('keeps writing available offline and marks offline status immediately', () => {
    const store = useSaveStateStore()
    const originalNavigator = global.window?.navigator

    Object.defineProperty(global.window, 'navigator', {
      value: { ...originalNavigator, onLine: false },
      configurable: true
    })

    const draft = store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: 'offline-title',
      content: 'offline-draft',
      version: 2,
      timestamp: 100
    })

    expect(draft).toMatchObject({
      chapterId: 'ch-1',
      content: 'offline-draft'
    })
    expect(store.saveStatus).toBe('offline')
    expect(store.pendingQueue).toHaveLength(1)
    expect(store.readLocalDraft({ workId: 'work-1', chapterId: 'ch-1' })).toMatchObject({
      content: 'offline-draft'
    })

    Object.defineProperty(global.window, 'navigator', {
      value: originalNavigator,
      configurable: true
    })
  })

  it('clears the local draft only after remote save succeeds', async () => {
    const store = useSaveStateStore()

    const draft = store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: 'title',
      content: 'saved-content',
      version: 3,
      timestamp: 100
    })

    await store.flushDraft({
      draft,
      save: vi.fn().mockResolvedValue({
        id: 'ch-1',
        version: 4
      })
    })

    expect(store.readLocalDraft({ workId: 'work-1', chapterId: 'ch-1' })).toBeNull()
    expect(store.pendingQueue).toEqual([])
    expect(store.saveStatus).toBe('synced')
  })

  it('keeps the local draft and exposes conflict state after 409', async () => {
    const store = useSaveStateStore()
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'version_conflict',
      server_version: 8
    }

    const draft = store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: 'conflict-title',
      content: 'local-conflict-draft',
      version: 7,
      timestamp: 100
    })

    await expect(store.flushDraft({
      draft,
      save: vi.fn().mockRejectedValue(conflictError)
    })).rejects.toThrow('conflict')

    expect(store.readLocalDraft({ workId: 'work-1', chapterId: 'ch-1' })).toMatchObject({
      content: 'local-conflict-draft'
    })
    expect(store.saveStatus).toBe('conflict')
    expect(store.hasConflict).toBe(true)
    expect(store.conflictPayload).toMatchObject({
      chapterId: 'ch-1',
      content: 'local-conflict-draft',
      server_version: 8
    })
  })

  it('keeps conflict payload and local draft when user cancels conflict handling', async () => {
    const store = useSaveStateStore()
    const draft = store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: '冲突标题',
      content: '保留中的本地草稿',
      version: 3,
      timestamp: 100
    })

    store.markConflict({
      ...draft,
      server_version: 4,
      server_content: 'server-copy'
    }, 'version_conflict')

    expect(store.hasConflict).toBe(true)
    expect(store.readLocalDraft({ workId: 'work-1', chapterId: 'ch-1' })).toMatchObject({
      content: '保留中的本地草稿'
    })
    expect(store.conflictPayload).toMatchObject({
      server_version: 4,
      server_content: 'server-copy'
    })
  })

  it('clears draft and conflict after override path succeeds', async () => {
    const store = useSaveStateStore()
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'version_conflict',
      server_version: 8
    }

    const draft = store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      title: '冲突标题',
      content: '本地覆盖内容',
      version: 7,
      timestamp: 100
    })

    await expect(store.flushDraft({
      draft,
      save: vi.fn().mockRejectedValue(conflictError)
    })).rejects.toThrow('conflict')

    const overrideSave = vi.fn().mockResolvedValue({
      id: 'ch-1',
      version: 9
    })

    await store.flushDraft({
      draft: {
        ...store.conflictPayload,
        workId: 'work-1',
        chapterId: 'ch-1',
        content: '本地覆盖内容',
        title: '冲突标题',
        version: 8
      },
      save: overrideSave
    })
    store.clearConflict()

    expect(overrideSave).toHaveBeenCalledWith(expect.objectContaining({
      chapterId: 'ch-1',
      content: '本地覆盖内容'
    }))
    expect(store.readLocalDraft({ workId: 'work-1', chapterId: 'ch-1' })).toBeNull()
    expect(store.pendingQueue).toEqual([])
    expect(store.hasConflict).toBe(false)
    expect(store.saveStatus).toBe('synced')
  })

  it('replays only the latest draft per chapter in timestamp order on network recovery', async () => {
    const store = useSaveStateStore()
    const replayed = []

    store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-2',
      content: 'chapter-2-old',
      timestamp: 20
    })
    store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      content: 'chapter-1',
      timestamp: 10
    })
    store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-2',
      content: 'chapter-2-latest',
      timestamp: 30
    })

    await store.handleNetworkOnline({
      workId: 'work-1',
      save: async (draft) => {
        replayed.push({
          chapterId: draft.chapterId,
          content: draft.content
        })
      }
    })

    expect(replayed).toEqual([
      { chapterId: 'ch-1', content: 'chapter-1' },
      { chapterId: 'ch-2', content: 'chapter-2-latest' }
    ])
    expect(store.pendingQueue).toEqual([])
    expect(store.collectLocalDrafts('work-1')).toEqual([])
  })

  it('flushes queued offline drafts on network recovery and returns to synced state', async () => {
    const store = useSaveStateStore()
    const replayed = []

    store.markOffline()
    store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-1',
      content: 'draft-a',
      timestamp: 10
    })
    store.writeLocalDraft({
      workId: 'work-1',
      chapterId: 'ch-2',
      content: 'draft-b',
      timestamp: 20
    })

    await store.handleNetworkOnline({
      workId: 'work-1',
      save: async (draft) => {
        replayed.push(draft.chapterId)
        return {
          id: draft.chapterId,
          version: Number(draft.version || 1) + 1
        }
      }
    })

    expect(replayed).toEqual(['ch-1', 'ch-2'])
    expect(store.pendingQueue).toEqual([])
    expect(store.collectLocalDrafts('work-1')).toEqual([])
    expect(store.saveStatus).toBe('synced')
  })
})
