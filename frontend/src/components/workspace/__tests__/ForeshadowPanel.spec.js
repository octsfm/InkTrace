import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { localCache } from '@/utils/localCache'
import { useWritingAssetStore } from '@/stores/writingAsset'
import ForeshadowPanel from '../ForeshadowPanel.vue'

const mockListForeshadows = vi.fn()
const mockCreateForeshadow = vi.fn()
const mockUpdateForeshadow = vi.fn()
const mockDeleteForeshadow = vi.fn()

vi.mock('@/api', () => ({
  v1WritingAssetsApi: {
    getWorkOutline: vi.fn(),
    saveWorkOutline: vi.fn(),
    getChapterOutline: vi.fn(),
    saveChapterOutline: vi.fn(),
    listTimeline: vi.fn().mockResolvedValue([]),
    createTimeline: vi.fn(),
    updateTimeline: vi.fn(),
    deleteTimeline: vi.fn(),
    reorderTimeline: vi.fn(),
    listForeshadows: (...args) => mockListForeshadows(...args),
    createForeshadow: (...args) => mockCreateForeshadow(...args),
    updateForeshadow: (...args) => mockUpdateForeshadow(...args),
    deleteForeshadow: (...args) => mockDeleteForeshadow(...args),
    listCharacters: vi.fn().mockResolvedValue([])
  }
}))

describe('ForeshadowPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localCache.clear()
    mockListForeshadows.mockReset()
    mockCreateForeshadow.mockReset()
    mockUpdateForeshadow.mockReset()
    mockDeleteForeshadow.mockReset()
  })

  it('loads open foreshadows by default and switches to resolved filter', async () => {
    mockListForeshadows
      .mockResolvedValueOnce([
        { id: 'f-1', title: '未回收', description: '', status: 'open', introduced_chapter_id: null, resolved_chapter_id: null, version: 1 }
      ])
      .mockResolvedValueOnce([
        { id: 'f-2', title: '已回收', description: '', status: 'resolved', introduced_chapter_id: null, resolved_chapter_id: null, version: 1 }
      ])

    const wrapper = mount(ForeshadowPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    expect(mockListForeshadows).toHaveBeenCalledWith('work-1', 'open')
    expect(wrapper.find('.foreshadow-item').attributes('data-item-id')).toBe('f-1')

    await wrapper.find('[data-status="resolved"]').trigger('click')
    await flushPromises()

    expect(mockListForeshadows).toHaveBeenCalledWith('work-1', 'resolved')
    expect(wrapper.find('.foreshadow-item').attributes('data-item-id')).toBe('f-2')
  })

  it('creates a new foreshadow with current status and chapter refs', async () => {
    mockListForeshadows.mockResolvedValue([])
    mockCreateForeshadow.mockResolvedValue({
      id: 'f-3',
      title: '新伏笔',
      description: '伏笔描述',
      status: 'resolved',
      introduced_chapter_id: 'chapter-1',
      resolved_chapter_id: 'chapter-2',
      version: 1
    })

    const wrapper = mount(ForeshadowPanel, {
      props: {
        workId: 'work-1',
        chapters: [
          { id: 'chapter-1', order_index: 1, title: '起点' },
          { id: 'chapter-2', order_index: 2, title: '回收' }
        ]
      }
    })
    await flushPromises()

    await wrapper.find('[data-status="resolved"]').trigger('click')
    await flushPromises()
    await wrapper.find('.create-button').trigger('click')
    await wrapper.find('[data-testid="foreshadow-title"]').setValue('新伏笔')
    await wrapper.find('[data-testid="foreshadow-description"]').setValue('伏笔描述')
    await wrapper.find('[data-testid="foreshadow-introduced"]').setValue('chapter-1')
    await wrapper.find('[data-testid="foreshadow-resolved"]').setValue('chapter-2')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockCreateForeshadow).toHaveBeenCalledWith('work-1', {
      title: '新伏笔',
      description: '伏笔描述',
      status: 'resolved',
      introduced_chapter_id: 'chapter-1',
      resolved_chapter_id: 'chapter-2'
    })
    expect(wrapper.find('.foreshadow-item').attributes('data-item-id')).toBe('f-3')
  })

  it('writes draft on edit and saves existing foreshadow with expected_version', async () => {
    mockListForeshadows.mockResolvedValue([
      {
        id: 'f-1',
        title: '原伏笔',
        description: '原描述',
        status: 'open',
        introduced_chapter_id: null,
        resolved_chapter_id: null,
        version: 3
      }
    ])
    mockUpdateForeshadow.mockResolvedValue({
      id: 'f-1',
      title: '已更新伏笔',
      description: '原描述',
      status: 'resolved',
      introduced_chapter_id: 'chapter-1',
      resolved_chapter_id: 'chapter-2',
      version: 4
    })

    const wrapper = mount(ForeshadowPanel, {
      props: {
        workId: 'work-1',
        chapters: [
          { id: 'chapter-1', order_index: 1, title: '引入' },
          { id: 'chapter-2', order_index: 2, title: '回收' }
        ]
      }
    })
    await flushPromises()

    await wrapper.find('[data-testid="foreshadow-title"]').setValue('已更新伏笔')
    await wrapper.find('[data-testid="foreshadow-status"]').setValue('resolved')
    await wrapper.find('[data-testid="foreshadow-introduced"]').setValue('chapter-1')
    await wrapper.find('[data-testid="foreshadow-resolved"]').setValue('chapter-2')

    const store = useWritingAssetStore()
    expect(store.assetDrafts['foreshadow:f-1']).toMatchObject({
      payload: {
        title: '已更新伏笔',
        status: 'resolved',
        introduced_chapter_id: 'chapter-1',
        resolved_chapter_id: 'chapter-2',
        expected_version: 3
      }
    })

    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockUpdateForeshadow).toHaveBeenCalledWith('f-1', {
      title: '已更新伏笔',
      description: '原描述',
      status: 'resolved',
      introduced_chapter_id: 'chapter-1',
      resolved_chapter_id: 'chapter-2',
      expected_version: 3
    })
  })

  it('keeps local draft and opens conflict modal after 409', async () => {
    mockListForeshadows.mockResolvedValue([
      {
        id: 'f-1',
        title: '原伏笔',
        description: '',
        status: 'open',
        introduced_chapter_id: null,
        resolved_chapter_id: null,
        version: 1
      }
    ])
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 2,
      resource_type: 'foreshadow',
      resource_id: 'f-1'
    }
    mockUpdateForeshadow.mockRejectedValue(conflictError)

    const wrapper = mount(ForeshadowPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="foreshadow-title"]').setValue('冲突伏笔')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(store.assetDrafts['foreshadow:f-1']).toMatchObject({
      payload: {
        title: '冲突伏笔'
      }
    })
    expect(wrapper.findComponent({ name: 'AssetConflictModal' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('资料版本冲突')
  })

  it('deletes the current foreshadow and removes it from the list', async () => {
    mockListForeshadows.mockResolvedValue([
      { id: 'f-1', title: '伏笔一', description: '', status: 'open', introduced_chapter_id: null, resolved_chapter_id: null, version: 1 },
      { id: 'f-2', title: '伏笔二', description: '', status: 'open', introduced_chapter_id: null, resolved_chapter_id: null, version: 1 }
    ])
    mockDeleteForeshadow.mockResolvedValue({ ok: true, id: 'f-1' })

    const wrapper = mount(ForeshadowPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-item-id="f-1"]').trigger('click')
    const deleteButton = wrapper.findAll('button').find((node) => node.text() === '删除')
    await deleteButton.trigger('click')
    await flushPromises()

    expect(mockDeleteForeshadow).toHaveBeenCalledWith('f-1')
    expect(wrapper.findAll('.foreshadow-item')).toHaveLength(1)
    expect(wrapper.find('.foreshadow-item').attributes('data-item-id')).toBe('f-2')
  })
})
