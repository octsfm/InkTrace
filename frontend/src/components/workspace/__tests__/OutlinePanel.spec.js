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

  it('loads work outline and uses work mode as the only visible editor by default', async () => {
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
    expect(wrapper.find('[data-testid="chapter-outline-text"]').exists()).toBe(false)
  })

  it('writes work draft on edit and shows dirty state', async () => {
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
    expect(wrapper.text()).toContain('未保存')
  })

  it('stages asset draft offline and only saves after explicit action', async () => {
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
    expect(wrapper.text()).toContain('资料版本冲突')
  })

  it('switches to chapter mode and loads saves chapter outline draft independently', async () => {
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

    await wrapper.get('[data-testid="outline-mode-chapter"]').trigger('click')
    await flushPromises()

    expect(mockGetChapterOutline).toHaveBeenCalledWith('chapter-1')
    expect(wrapper.find('[data-testid="work-outline-text"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="chapter-outline-text"]').element.value).toBe('远端章节细纲')

    await wrapper.find('[data-testid="chapter-outline-text"]').setValue('章节细纲草稿')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockSaveChapterOutline).toHaveBeenCalledWith('chapter-1', {
      content_text: '章节细纲草稿',
      content_tree_json: [],
      expected_version: 4
    })
    expect(useWritingAssetStore().assetDrafts['chapter_outline:chapter-1']).toBeUndefined()
  })

  it('guards mode switching with cancel save and discard branches without losing drafts', async () => {
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
      content_text: '章节远端',
      content_tree_json: [],
      version: 3
    })
    mockSaveWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '待切换作品大纲',
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

    await wrapper.find('[data-testid="work-outline-text"]').setValue('待切换作品大纲')
    await wrapper.get('[data-testid="outline-mode-chapter"]').trigger('click')
    expect(wrapper.find('.mode-switch-guard').exists()).toBe(true)

    await wrapper.findAll('.mode-switch-guard-actions button')[2].trigger('click')
    expect(wrapper.find('[data-testid="work-outline-text"]').exists()).toBe(true)
    expect(mockSaveWorkOutline).not.toHaveBeenCalled()

    await wrapper.get('[data-testid="outline-mode-chapter"]').trigger('click')
    await wrapper.findAll('.mode-switch-guard-actions button')[0].trigger('click')
    await flushPromises()
    expect(mockSaveWorkOutline).toHaveBeenCalledWith('work-1', {
      content_text: '待切换作品大纲',
      content_tree_json: [],
      expected_version: 1
    })
    expect(wrapper.find('[data-testid="chapter-outline-text"]').exists()).toBe(true)

    await wrapper.find('[data-testid="chapter-outline-text"]').setValue('章节本地草稿')
    await wrapper.get('[data-testid="outline-mode-work"]').trigger('click')
    await wrapper.findAll('.mode-switch-guard-actions button')[1].trigger('click')
    await flushPromises()

    expect(useWritingAssetStore().assetDrafts['chapter_outline:chapter-1']).toBeUndefined()
    expect(wrapper.find('[data-testid="work-outline-text"]').exists()).toBe(true)
  })

  it('does not expose outline import controls inside the writing workspace panel', async () => {
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

    expect(wrapper.text()).not.toContain('导入大纲')
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('outline_file')
  })
})
