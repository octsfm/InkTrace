import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { localCache } from '@/utils/localCache'
import { useWritingAssetStore } from '@/stores/writingAsset'
import OutlinePanel from '../OutlinePanel.vue'

const mockGetWorkOutline = vi.fn()
const mockGetChapterOutline = vi.fn()
const mockSaveWorkOutline = vi.fn()
const mockSaveChapterOutline = vi.fn()

vi.mock('@/api', () => ({
  v1WritingAssetsApi: {
    getWorkOutline: (...args) => mockGetWorkOutline(...args),
    saveWorkOutline: (...args) => mockSaveWorkOutline(...args),
    getChapterOutline: (...args) => mockGetChapterOutline(...args),
    saveChapterOutline: (...args) => mockSaveChapterOutline(...args),
    listTimeline: vi.fn().mockResolvedValue([]),
    listForeshadows: vi.fn().mockResolvedValue([]),
    listCharacters: vi.fn().mockResolvedValue([])
  }
}))

describe('OutlinePanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localCache.clear()
    mockGetWorkOutline.mockReset()
    mockGetChapterOutline.mockReset()
    mockSaveWorkOutline.mockReset()
    mockSaveChapterOutline.mockReset()
  })

  it('loads work outline and renders content_text as edit source', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '远端大纲',
      content_tree_json: [],
      version: 1
    })

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    expect(mockGetWorkOutline).toHaveBeenCalledWith('work-1')
    expect(wrapper.find('[data-testid="work-outline-text"]').element.value).toBe('远端大纲')
  })

  it('writes draft on edit and shows dirty state', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '',
      content_tree_json: [],
      version: 1
    })
    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="work-outline-text"]').setValue('本地大纲草稿')

    const store = useWritingAssetStore()
    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '本地大纲草稿',
        expected_version: 1
      }
    })
    expect(wrapper.text()).toContain('Unsaved')
  })

  it('stages asset draft offline and does not auto-submit after network recovery', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '',
      content_tree_json: [],
      version: 1
    })
    mockSaveWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '离线大纲草稿',
      content_tree_json: [],
      version: 2
    })
    const originalNavigator = global.window?.navigator
    Object.defineProperty(global.window, 'navigator', {
      value: { ...originalNavigator, onLine: false },
      configurable: true
    })

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="work-outline-text"]').setValue('离线大纲草稿')

    const store = useWritingAssetStore()
    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '离线大纲草稿'
      }
    })
    expect(localCache.get('asset_draft:work_outline:work')).toMatchObject({
      payload: {
        content_text: '离线大纲草稿'
      }
    })
    expect(mockSaveWorkOutline).not.toHaveBeenCalled()

    Object.defineProperty(global.window, 'navigator', {
      value: { ...originalNavigator, onLine: true },
      configurable: true
    })
    await flushPromises()

    expect(mockSaveWorkOutline).not.toHaveBeenCalled()

    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockSaveWorkOutline).toHaveBeenCalledWith('work-1', {
      content_text: '离线大纲草稿',
      content_tree_json: [],
      expected_version: 1
    })
    expect(store.assetDrafts['work_outline:work']).toBeUndefined()

    Object.defineProperty(global.window, 'navigator', {
      value: originalNavigator,
      configurable: true
    })
  })

  it('explicitly saves with expected_version and clears dirty state', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '',
      content_tree_json: [],
      version: 1
    })
    mockSaveWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '已保存大纲',
      content_tree_json: [],
      version: 2
    })
    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="work-outline-text"]').setValue('已保存大纲')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockSaveWorkOutline).toHaveBeenCalledWith('work-1', {
      content_text: '已保存大纲',
      content_tree_json: [],
      expected_version: 1
    })
    expect(useWritingAssetStore().dirtyAssetKeys).toEqual([])
  })

  it('keeps local draft and opens conflict modal after 409', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '',
      content_tree_json: [],
      version: 1
    })
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 2,
      resource_type: 'work_outline',
      resource_id: 'outline-1'
    }
    mockSaveWorkOutline.mockRejectedValue(conflictError)
    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="work-outline-text"]').setValue('冲突大纲')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '冲突大纲'
      }
    })
    expect(wrapper.findComponent({ name: 'AssetConflictModal' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('Asset version conflict')
  })

  it('loads and saves current chapter outline with chapter-specific draft', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '',
      content_tree_json: [],
      version: 1
    })
    mockGetChapterOutline.mockResolvedValue({
      id: 'chapter-outline-1',
      chapter_id: 'chapter-1',
      content_text: '远端章节细纲',
      content_tree_json: [],
      version: 4
    })
    mockSaveChapterOutline.mockResolvedValue({
      id: 'chapter-outline-1',
      chapter_id: 'chapter-1',
      content_text: '章节细纲草稿',
      content_tree_json: [],
      version: 5
    })
    const wrapper = mount(OutlinePanel, {
      props: {
        workId: 'work-1',
        activeChapterId: 'chapter-1'
      }
    })
    await flushPromises()

    expect(mockGetChapterOutline).toHaveBeenCalledWith('chapter-1')
    expect(wrapper.find('[data-testid="chapter-outline-text"]').element.value).toBe('远端章节细纲')

    await wrapper.find('[data-testid="chapter-outline-text"]').setValue('章节细纲草稿')
    await wrapper.findAll('.save-button')[1].trigger('click')
    await flushPromises()

    expect(mockSaveChapterOutline).toHaveBeenCalledWith('chapter-1', {
      content_text: '章节细纲草稿',
      content_tree_json: [],
      expected_version: 4
    })
    expect(useWritingAssetStore().assetDrafts['chapter_outline:chapter-1']).toBeUndefined()
  })

  it('supports save discard cancel decisions before switching dirty chapter outline', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '',
      content_tree_json: [],
      version: 1
    })
    mockGetChapterOutline.mockImplementation(async (chapterId) => ({
      id: `outline-${chapterId}`,
      chapter_id: chapterId,
      content_text: `${chapterId} remote`,
      content_tree_json: [],
      version: 1
    }))
    mockSaveChapterOutline.mockResolvedValue({
      id: 'outline-chapter-1',
      chapter_id: 'chapter-1',
      content_text: 'dirty outline',
      content_tree_json: [],
      version: 2
    })
    const wrapper = mount(OutlinePanel, {
      props: {
        workId: 'work-1',
        activeChapterId: 'chapter-1'
      }
    })
    await flushPromises()
    await wrapper.find('[data-testid="chapter-outline-text"]').setValue('dirty outline')

    const store = useWritingAssetStore()

    await expect(store.prepareChapterOutlineSwitch({
      currentChapterId: 'chapter-1',
      nextChapterId: 'chapter-2',
      decision: 'cancel'
    })).resolves.toBe(false)
    expect(mockGetChapterOutline).not.toHaveBeenCalledWith('chapter-2')

    await expect(store.prepareChapterOutlineSwitch({
      currentChapterId: 'chapter-1',
      nextChapterId: 'chapter-2',
      decision: 'save'
    })).resolves.toBe(true)
    expect(mockSaveChapterOutline).toHaveBeenCalledWith('chapter-1', {
      content_text: 'dirty outline',
      content_tree_json: [],
      expected_version: 1
    })
    expect(mockGetChapterOutline).toHaveBeenCalledWith('chapter-2')

    store.writeAssetDraft('chapter_outline', 'chapter-2', {
      content_text: 'second dirty',
      content_tree_json: [],
      expected_version: 1
    })
    await expect(store.prepareChapterOutlineSwitch({
      currentChapterId: 'chapter-2',
      nextChapterId: 'chapter-3',
      decision: 'discard'
    })).resolves.toBe(true)
    expect(store.assetDrafts['chapter_outline:chapter-2']).toBeUndefined()
    expect(mockGetChapterOutline).toHaveBeenCalledWith('chapter-3')
  })
})
