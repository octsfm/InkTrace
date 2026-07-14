import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { localCache } from '@/utils/localCache'
import { useSaveStateStore } from '../useSaveStateStore'
import { useWritingAssetStore } from '../writingAsset'

const mockGetWorkOutline = vi.fn()
const mockGetChapterOutline = vi.fn()
const mockListTimeline = vi.fn()
const mockListForeshadows = vi.fn()
const mockListCharacters = vi.fn()
const mockSaveWorkOutline = vi.fn()
const mockReorderTimeline = vi.fn()
const mockUpdateForeshadow = vi.fn()
const mockCreateCharacter = vi.fn()
const mockUpdateCharacter = vi.fn()
const mockDeleteCharacter = vi.fn()
const mockGetContextPackReadiness = vi.fn()

vi.mock('@/api', () => ({
  v1WritingAssetsApi: {
    getWorkOutline: (...args) => mockGetWorkOutline(...args),
    getChapterOutline: (...args) => mockGetChapterOutline(...args),
    listTimeline: (...args) => mockListTimeline(...args),
    listForeshadows: (...args) => mockListForeshadows(...args),
    listCharacters: (...args) => mockListCharacters(...args),
    saveWorkOutline: (...args) => mockSaveWorkOutline(...args),
    reorderTimeline: (...args) => mockReorderTimeline(...args),
    updateForeshadow: (...args) => mockUpdateForeshadow(...args),
    createCharacter: (...args) => mockCreateCharacter(...args),
    updateCharacter: (...args) => mockUpdateCharacter(...args),
    deleteCharacter: (...args) => mockDeleteCharacter(...args)
  },
  aiApi: {
    getContextPackReadiness: (...args) => mockGetContextPackReadiness(...args)
  }
}))

describe('useWritingAssetStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGetWorkOutline.mockReset()
    mockGetChapterOutline.mockReset()
    mockListTimeline.mockReset()
    mockListForeshadows.mockReset()
    mockListCharacters.mockReset()
    mockSaveWorkOutline.mockReset()
    mockReorderTimeline.mockReset()
    mockUpdateForeshadow.mockReset()
    mockCreateCharacter.mockReset()
    mockUpdateCharacter.mockReset()
    mockDeleteCharacter.mockReset()
    mockGetContextPackReadiness.mockReset()
    localCache.clear()
  })

  it('loads four writing asset groups through v1 APIs', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '全书大纲',
      version: 1
    })
    mockListTimeline.mockResolvedValue([{ id: 'event-1', order_index: 1 }])
    mockListForeshadows.mockResolvedValue([{ id: 'foreshadow-1', status: 'open' }])
    mockListCharacters.mockResolvedValue([{ id: 'character-1', name: '林舟', aliases: [] }])

    const store = useWritingAssetStore()
    const result = await store.loadAllAssets('work-1')

    expect(mockGetWorkOutline).toHaveBeenCalledWith('work-1')
    expect(mockListTimeline).toHaveBeenCalledWith('work-1')
    expect(mockListForeshadows).toHaveBeenCalledWith('work-1', 'open')
    expect(mockListCharacters).toHaveBeenCalledWith('work-1', '')
    expect(result.workOutline.content_text).toBe('全书大纲')
    expect(store.assets.timeline).toEqual([{ id: 'event-1', order_index: 1 }])
    expect(store.assets.foreshadow).toEqual([{ id: 'foreshadow-1', status: 'open' }])
    expect(store.assets.character).toEqual([{ id: 'character-1', name: '林舟', aliases: [] }])
  })

  it('loads plot arc readiness summary for the active chapter without touching structured asset drafts', async () => {
    mockGetContextPackReadiness.mockResolvedValue({
      data: {
        status: 'degraded',
        warnings: ['volume_arc_missing', 'sequence_arc_missing'],
        plot_arc_statuses: {
          master_arc: { status: 'ready', quality_level: 'minimal', warning_codes: [] },
          volume_arc: { status: 'pending', quality_level: 'placeholder', warning_codes: ['arc_placeholder_only'] },
          sequence_arc: { status: 'pending', quality_level: 'placeholder', warning_codes: ['arc_placeholder_only'] },
          immediate_window: { status: 'ready', quality_level: 'complete', warning_codes: [] }
        },
        plot_arc_summary: {
          master_arc: { arc_title: '灯塔迷局', ultimate_goal: '揭开海雾秘密', current_stage: '追查旧地图', core_theme: '真相与代价' },
          volume_arc: { stage_goal: '确认灯塔背后的势力', stage_open_loops: ['地图来源'], key_characters: ['顾迟'] },
          sequence_arc: { sequence_goal: '完成第一轮追索', key_events: ['发现旧地图'] },
          immediate_window: { active_plot_threads: ['灯塔谜团'], recent_chapters_summary: ['顾迟进入灯塔'] }
        }
      }
    })

    const store = useWritingAssetStore()
    const payload = await store.loadPlotArcContext('work-1', 'chapter-1')

    expect(mockGetContextPackReadiness).toHaveBeenCalledWith('work-1', 'chapter-1')
    expect(payload.status).toBe('degraded')
    expect(store.contextPackReadiness.status).toBe('degraded')
    expect(store.plotArcSummary.master_arc.arc_title).toBe('灯塔迷局')
    expect(store.plotArcStatuses.volume_arc.status).toBe('pending')
    expect(store.assetDrafts).toEqual({})
  })

  it('writes in-memory asset drafts and marks dirty state', () => {
    const store = useWritingAssetStore()
    store.setWorkContext('work-1')

    const draft = store.writeAssetDraft('work_outline', 'work', {
      content_text: '本地草稿',
      expected_version: 1
    })

    expect(draft).toMatchObject({
      asset_type: 'work_outline',
      asset_id: 'work',
      payload: {
        content_text: '本地草稿',
        expected_version: 1
      }
    })
    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '本地草稿'
      }
    })
    expect(store.dirtyAssetKeys).toEqual(['work_outline:work'])
    expect(store.getAssetSaveStatus('work_outline', 'work')).toBe('dirty')
    expect(localCache.get('asset_draft:work_outline:work-1')).toMatchObject({
      payload: {
        content_text: '本地草稿'
      }
    })
  })

  it('restores asset draft from local cache', () => {
    localCache.set('asset_draft:chapter_outline:chapter-1', {
      asset_type: 'chapter_outline',
      asset_id: 'chapter-1',
      payload: {
        content_text: '章节细纲暂存'
      },
      timestamp: 100
    })
    const store = useWritingAssetStore()

    const draft = store.readAssetDraft('chapter_outline', 'chapter-1')

    expect(draft).toMatchObject({
      asset_type: 'chapter_outline',
      asset_id: 'chapter-1',
      payload: {
        content_text: '章节细纲暂存'
      }
    })
    expect(store.dirtyAssetKeys).toEqual(['chapter_outline:chapter-1'])
  })

  it('keeps work outline drafts isolated by work id', () => {
    const store = useWritingAssetStore()

    store.setWorkContext('work-1')
    store.writeAssetDraft('work_outline', 'work', {
      content_text: '作品一的大纲',
      expected_version: 1
    })

    store.setWorkContext('work-2')
    store.writeAssetDraft('work_outline', 'work', {
      content_text: '作品二的大纲',
      expected_version: 1
    })

    expect(localCache.get('asset_draft:work_outline:work-1')).toMatchObject({
      payload: { content_text: '作品一的大纲' }
    })
    expect(localCache.get('asset_draft:work_outline:work-2')).toMatchObject({
      payload: { content_text: '作品二的大纲' }
    })
    expect(localCache.get('asset_draft:work_outline:work')).toBeNull()

    store.setWorkContext('work-1')
    const restored = store.readAssetDraft('work_outline', 'work')

    expect(restored).toMatchObject({
      payload: { content_text: '作品一的大纲' }
    })
  })

  it('clears draft only after successful explicit save', async () => {
    mockSaveWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '已保存',
      version: 2
    })
    const store = useWritingAssetStore()
    store.setWorkContext('work-1')
    store.writeAssetDraft('work_outline', 'work', {
      content_text: '已保存',
      expected_version: 1
    })

    const saved = await store.saveWorkOutline()

    expect(mockSaveWorkOutline).toHaveBeenCalledWith('work-1', {
      content_text: '已保存',
      expected_version: 1
    })
    expect(saved.version).toBe(2)
    expect(store.assetDrafts).toEqual({})
    expect(localCache.get('asset_draft:work_outline:work-1')).toBeNull()
    expect(store.dirtyAssetKeys).toEqual([])
    expect(store.getAssetSaveStatus('work_outline', 'work')).toBe('synced')
  })

  it('keeps draft and exposes conflict payload after 409', async () => {
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 3,
      resource_type: 'work_outline',
      resource_id: 'outline-1'
    }
    mockSaveWorkOutline.mockRejectedValue(conflictError)

    const store = useWritingAssetStore()
    store.setWorkContext('work-1')
    store.writeAssetDraft('work_outline', 'work', {
      content_text: '冲突草稿',
      expected_version: 2
    })

    await expect(store.saveWorkOutline()).rejects.toThrow('conflict')

    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '冲突草稿'
      }
    })
    expect(localCache.get('asset_draft:work_outline:work-1')).toMatchObject({
      payload: {
        content_text: '冲突草稿'
      }
    })
    expect(store.assetConflictPayload).toMatchObject({
      asset_type: 'work_outline',
      asset_id: 'work',
      detail: 'asset_version_conflict',
      server_version: 3
    })
    expect(store.getAssetSaveStatus('work_outline', 'work')).toBe('conflict')
  })

  it('keeps asset drafts isolated from chapter replay queue', () => {
    const assetStore = useWritingAssetStore()
    const saveStateStore = useSaveStateStore()

    assetStore.writeAssetDraft('timeline', 'event-1', {
      title: '时间线草稿',
      expected_version: 1
    })
    assetStore.writeAssetDraft('character', 'character-1', {
      name: '人物草稿',
      aliases: ['A']
    })

    expect(Object.keys(assetStore.assetDrafts)).toEqual(['timeline:event-1', 'character:character-1'])
    expect(saveStateStore.pendingQueue).toEqual([])
    expect(localCache.get('asset_draft:timeline:event-1')).toMatchObject({
      payload: { title: '时间线草稿' }
    })
  })

  it('reorders timeline with full mapping and clears reorder draft after success', async () => {
    mockReorderTimeline.mockResolvedValue([
      { id: 'event-2', title: '二', order_index: 1 },
      { id: 'event-1', title: '一', order_index: 2 }
    ])
    const store = useWritingAssetStore()
    store.setWorkContext('work-1')
    store.timeline = [
      { id: 'event-1', title: '一', order_index: 1 },
      { id: 'event-2', title: '二', order_index: 2 }
    ]
    store.assets.timeline = store.timeline

    store.stageTimelineReorder([
      { id: 'event-2', title: '二', order_index: 2 },
      { id: 'event-1', title: '一', order_index: 1 }
    ])
    const reordered = await store.reorderTimelineEvents()

    expect(mockReorderTimeline).toHaveBeenCalledWith('work-1', [
      { id: 'event-2', order_index: 1 },
      { id: 'event-1', order_index: 2 }
    ])
    expect(reordered.map((item) => item.id)).toEqual(['event-2', 'event-1'])
    expect(store.assetDrafts['timeline:__reorder__']).toBeUndefined()
    expect(store.getAssetSaveStatus('timeline', '__reorder__')).toBe('synced')
  })

  it('keeps foreshadow draft after conflict and marks conflict payload', async () => {
    const conflictError = new Error('foreshadow conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 4,
      resource_type: 'foreshadow',
      resource_id: 'foreshadow-1'
    }
    mockUpdateForeshadow.mockRejectedValue(conflictError)

    const store = useWritingAssetStore()
    store.setWorkContext('work-1')
    store.foreshadows = [{
      id: 'foreshadow-1',
      title: '伏笔',
      status: 'open',
      version: 3
    }]
    store.writeAssetDraft('foreshadow', 'foreshadow-1', {
      title: '伏笔',
      status: 'resolved',
      expected_version: 3
    })

    await expect(store.updateForeshadow('foreshadow-1')).rejects.toThrow('foreshadow conflict')

    expect(store.assetDrafts['foreshadow:foreshadow-1']).toMatchObject({
      payload: { status: 'resolved' }
    })
    expect(store.assetConflictPayload).toMatchObject({
      asset_type: 'foreshadow',
      asset_id: 'foreshadow-1',
      server_version: 4
    })
    expect(store.getAssetSaveStatus('foreshadow', 'foreshadow-1')).toBe('conflict')
  })

  it('keeps asset draft after canceling conflict handling until user decides', async () => {
    const conflictError = new Error('character conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 5,
      resource_type: 'character',
      resource_id: 'character-1',
      server_content: 'server-copy'
    }
    mockUpdateCharacter.mockRejectedValue(conflictError)

    const store = useWritingAssetStore()
    store.setWorkContext('work-1')
    store.characters = [{
      id: 'character-1',
      name: '林舟',
      aliases: ['舟'],
      description: '主角',
      version: 4
    }]
    store.writeAssetDraft('character', 'character-1', {
      name: '林舟',
      aliases: ['舟', 'Lin'],
      description: '本地人物稿',
      expected_version: 4
    })

    await expect(store.updateCharacter('character-1')).rejects.toThrow('character conflict')

    store.clearAssetConflict()

    expect(store.assetDrafts['character:character-1']).toMatchObject({
      payload: {
        description: '本地人物稿'
      }
    })
    expect(localCache.get('asset_draft:character:character-1')).toMatchObject({
      payload: {
        description: '本地人物稿'
      }
    })
    expect(store.assetConflictPayload).toBeNull()
    expect(store.getAssetSaveStatus('character', 'character-1')).toBe('conflict')
  })

  it('creates updates and deletes character assets through store actions', async () => {
    mockCreateCharacter.mockResolvedValue({
      id: 'character-1',
      name: '林舟',
      aliases: ['舟'],
      description: '主角',
      version: 1
    })
    mockUpdateCharacter.mockResolvedValue({
      id: 'character-1',
      name: '林舟',
      aliases: ['舟', 'Lin'],
      description: '主角',
      version: 2
    })
    mockDeleteCharacter.mockResolvedValue({ ok: true })

    const store = useWritingAssetStore()
    store.setWorkContext('work-1')

    const created = await store.createCharacter({
      name: '林舟',
      aliases: ['舟'],
      description: '主角'
    })
    store.writeAssetDraft('character', 'character-1', {
      name: '林舟',
      aliases: ['舟', 'Lin'],
      description: '主角',
      expected_version: 1
    })
    const updated = await store.updateCharacter('character-1')
    const removed = await store.deleteCharacter('character-1')

    expect(created.version).toBe(1)
    expect(mockCreateCharacter).toHaveBeenCalledWith('work-1', {
      name: '林舟',
      aliases: ['舟'],
      description: '主角'
    })
    expect(mockUpdateCharacter).toHaveBeenCalledWith('character-1', {
      name: '林舟',
      aliases: ['舟', 'Lin'],
      description: '主角',
      expected_version: 1
    })
    expect(updated.version).toBe(2)
    expect(mockDeleteCharacter).toHaveBeenCalledWith('character-1')
    expect(removed).toEqual({ ok: true })
    expect(store.characters).toEqual([])
    expect(store.assetDrafts['character:character-1']).toBeUndefined()
  })
})
