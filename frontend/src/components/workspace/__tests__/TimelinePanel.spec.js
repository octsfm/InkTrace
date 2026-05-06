import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { localCache } from '@/utils/localCache'
import { useWritingAssetStore } from '@/stores/writingAsset'
import TimelinePanel from '../TimelinePanel.vue'

const mockListTimeline = vi.fn()
const mockCreateTimeline = vi.fn()
const mockUpdateTimeline = vi.fn()
const mockDeleteTimeline = vi.fn()
const mockReorderTimeline = vi.fn()

vi.mock('@/api', () => ({
  v1WritingAssetsApi: {
    getWorkOutline: vi.fn(),
    saveWorkOutline: vi.fn(),
    getChapterOutline: vi.fn(),
    saveChapterOutline: vi.fn(),
    listTimeline: (...args) => mockListTimeline(...args),
    createTimeline: (...args) => mockCreateTimeline(...args),
    updateTimeline: (...args) => mockUpdateTimeline(...args),
    deleteTimeline: (...args) => mockDeleteTimeline(...args),
    reorderTimeline: (...args) => mockReorderTimeline(...args),
    listForeshadows: vi.fn().mockResolvedValue([]),
    listCharacters: vi.fn().mockResolvedValue([])
  }
}))

describe('TimelinePanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localCache.clear()
    mockListTimeline.mockReset()
    mockCreateTimeline.mockReset()
    mockUpdateTimeline.mockReset()
    mockDeleteTimeline.mockReset()
    mockReorderTimeline.mockReset()
  })

  it('loads timeline events in order_index asc order', async () => {
    mockListTimeline.mockResolvedValue([
      { id: 'event-2', order_index: 2, title: '事件二', description: '', chapter_id: null, version: 1 },
      { id: 'event-1', order_index: 1, title: '事件一', description: '', chapter_id: null, version: 1 }
    ])

    const wrapper = mount(TimelinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    const items = wrapper.findAll('.timeline-item')
    expect(mockListTimeline).toHaveBeenCalledWith('work-1')
    expect(items).toHaveLength(2)
    expect(items[0].attributes('data-event-id')).toBe('event-1')
    expect(items[1].attributes('data-event-id')).toBe('event-2')
  })

  it('creates a new timeline event from explicit save', async () => {
    mockListTimeline.mockResolvedValue([])
    mockCreateTimeline.mockResolvedValue({
      id: 'event-3',
      order_index: 1,
      title: '新事件',
      description: '创建描述',
      chapter_id: 'chapter-1',
      version: 1
    })

    const wrapper = mount(TimelinePanel, {
      props: {
        workId: 'work-1',
        chapters: [{ id: 'chapter-1', order_index: 1, title: '起点' }]
      }
    })
    await flushPromises()

    await wrapper.find('.create-button').trigger('click')
    await wrapper.find('[data-testid="timeline-title"]').setValue('新事件')
    await wrapper.find('[data-testid="timeline-description"]').setValue('创建描述')
    await wrapper.find('[data-testid="timeline-chapter"]').setValue('chapter-1')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockCreateTimeline).toHaveBeenCalledWith('work-1', {
      title: '新事件',
      description: '创建描述',
      chapter_id: 'chapter-1'
    })
    expect(wrapper.find('.timeline-item').attributes('data-event-id')).toBe('event-3')
  })

  it('writes draft on edit and saves existing event with expected_version', async () => {
    mockListTimeline.mockResolvedValue([
      {
        id: 'event-1',
        order_index: 1,
        title: '原事件',
        description: '原描述',
        chapter_id: null,
        version: 4
      }
    ])
    mockUpdateTimeline.mockResolvedValue({
      id: 'event-1',
      order_index: 1,
      title: '已更新事件',
      description: '原描述',
      chapter_id: 'chapter-2',
      version: 5
    })

    const wrapper = mount(TimelinePanel, {
      props: {
        workId: 'work-1',
        chapters: [{ id: 'chapter-2', order_index: 2, title: '转折' }]
      }
    })
    await flushPromises()

    await wrapper.find('[data-testid="timeline-title"]').setValue('已更新事件')
    await wrapper.find('[data-testid="timeline-chapter"]').setValue('chapter-2')

    const store = useWritingAssetStore()
    expect(store.assetDrafts['timeline:event-1']).toMatchObject({
      payload: {
        title: '已更新事件',
        chapter_id: 'chapter-2',
        expected_version: 4
      }
    })

    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockUpdateTimeline).toHaveBeenCalledWith('event-1', {
      title: '已更新事件',
      description: '原描述',
      chapter_id: 'chapter-2',
      expected_version: 4
    })
    expect(store.assetDrafts['timeline:event-1']).toBeUndefined()
  })

  it('keeps local draft and opens conflict modal after 409', async () => {
    mockListTimeline.mockResolvedValue([
      {
        id: 'event-1',
        order_index: 1,
        title: '原事件',
        description: '',
        chapter_id: null,
        version: 1
      }
    ])
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 2,
      resource_type: 'timeline_event',
      resource_id: 'event-1'
    }
    mockUpdateTimeline.mockRejectedValue(conflictError)

    const wrapper = mount(TimelinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="timeline-title"]').setValue('冲突事件')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(store.assetDrafts['timeline:event-1']).toMatchObject({
      payload: {
        title: '冲突事件'
      }
    })
    expect(wrapper.findComponent({ name: 'AssetConflictModal' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('Asset version conflict')
  })

  it('deletes the current event and removes it from the list', async () => {
    mockListTimeline.mockResolvedValue([
      { id: 'event-1', order_index: 1, title: '事件一', description: '', chapter_id: null, version: 1 },
      { id: 'event-2', order_index: 2, title: '事件二', description: '', chapter_id: null, version: 1 }
    ])
    mockDeleteTimeline.mockResolvedValue({ ok: true, id: 'event-1' })

    const wrapper = mount(TimelinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-event-id="event-1"]').trigger('click')
    const deleteButton = wrapper.findAll('button').find((node) => node.text() === 'Delete')
    await deleteButton.trigger('click')
    await flushPromises()

    expect(mockDeleteTimeline).toHaveBeenCalledWith('event-1')
    expect(wrapper.findAll('.timeline-item')).toHaveLength(1)
    expect(wrapper.find('.timeline-item').attributes('data-event-id')).toBe('event-2')
  })

  it('moves timeline events locally and saves full reorder mappings', async () => {
    mockListTimeline.mockResolvedValue([
      { id: 'event-1', order_index: 1, title: '事件一', description: '', chapter_id: null, version: 1 },
      { id: 'event-2', order_index: 2, title: '事件二', description: '', chapter_id: null, version: 1 },
      { id: 'event-3', order_index: 3, title: '事件三', description: '', chapter_id: null, version: 1 }
    ])
    mockReorderTimeline.mockResolvedValue([
      { id: 'event-2', order_index: 1, title: '事件二', description: '', chapter_id: null, version: 2 },
      { id: 'event-1', order_index: 2, title: '事件一', description: '', chapter_id: null, version: 2 },
      { id: 'event-3', order_index: 3, title: '事件三', description: '', chapter_id: null, version: 2 }
    ])

    const wrapper = mount(TimelinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-event-id="event-2"]').trigger('click')
    await wrapper.find('[data-testid="timeline-move-up"]').trigger('click')

    const reorderedLocally = wrapper.findAll('.timeline-item')
    expect(reorderedLocally[0].attributes('data-event-id')).toBe('event-2')
    expect(reorderedLocally[1].attributes('data-event-id')).toBe('event-1')

    const store = useWritingAssetStore()
    expect(store.assetDrafts['timeline:__reorder__']).toMatchObject({
      payload: {
        items: [
          { id: 'event-2', order_index: 1 },
          { id: 'event-1', order_index: 2 },
          { id: 'event-3', order_index: 3 }
        ]
      }
    })

    await wrapper.find('[data-testid="timeline-save-order"]').trigger('click')
    await flushPromises()

    expect(mockReorderTimeline).toHaveBeenCalledWith('work-1', [
      { id: 'event-2', order_index: 1 },
      { id: 'event-1', order_index: 2 },
      { id: 'event-3', order_index: 3 }
    ])
    expect(store.assetDrafts['timeline:__reorder__']).toBeUndefined()
    expect(wrapper.findAll('.timeline-item')[0].attributes('data-event-id')).toBe('event-2')
  })
})
