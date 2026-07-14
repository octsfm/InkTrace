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
const mockGetContextPackReadiness = vi.fn()

vi.mock('@/api', () => ({
  v1WritingAssetsApi: {
    getWorkOutline: (...args) => mockGetWorkOutline(...args),
    saveWorkOutline: (...args) => mockSaveWorkOutline(...args),
    getChapterOutline: (...args) => mockGetChapterOutline(...args),
    saveChapterOutline: (...args) => mockSaveChapterOutline(...args),
    listTimeline: vi.fn().mockResolvedValue([]),
    listForeshadows: vi.fn().mockResolvedValue([]),
    listCharacters: vi.fn().mockResolvedValue([])
  },
  aiApi: {
    getContextPackReadiness: (...args) => mockGetContextPackReadiness(...args)
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
    mockGetContextPackReadiness.mockReset()
    mockGetContextPackReadiness.mockResolvedValue({
      data: {
        status: 'degraded',
        plot_arc_statuses: {
          master_arc: { status: 'ready', quality_level: 'minimal', warning_codes: [] },
          volume_arc: { status: 'pending', quality_level: 'placeholder', warning_codes: ['arc_placeholder_only'] },
          sequence_arc: { status: 'ready', quality_level: 'minimal', warning_codes: [] },
          immediate_window: { status: 'ready', quality_level: 'complete', warning_codes: [] }
        },
        plot_arc_summary: {
          master_arc: { arc_title: '灯塔迷局', current_stage: '追查旧地图', ultimate_goal: '揭开海雾秘密' },
          volume_arc: { stage_goal: '确认灯塔背后的势力' },
          sequence_arc: { sequence_goal: '完成第一轮追索', key_events: ['发现旧地图'] },
          immediate_window: { recent_chapters_summary: ['顾迟进入灯塔'] }
        }
      }
    })
  })

  it('shows import entry only in work outline mode and opens the modal without saving', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '远端大纲',
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

    const wrapper = mount(OutlinePanel, {
      props: {
        workId: 'work-1',
        activeChapterId: 'chapter-1'
      }
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="outline-import-trigger"]').exists()).toBe(true)
    await wrapper.get('[data-testid="outline-import-trigger"]').trigger('click')
    expect(wrapper.findComponent({ name: 'OutlineImportModal' }).props('visible')).toBe(true)
    expect(mockSaveWorkOutline).not.toHaveBeenCalled()

    await wrapper.get('[data-testid="outline-mode-chapter"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="outline-import-trigger"]').exists()).toBe(false)
  })

  it('shows plot arc summary in outline mode for the active chapter context', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '远端大纲',
      content_tree_json: [],
      version: 1
    })

    const wrapper = mount(OutlinePanel, {
      props: {
        workId: 'work-1',
        activeChapterId: 'chapter-1'
      }
    })
    await flushPromises()

    expect(mockGetContextPackReadiness).toHaveBeenCalledWith('work-1', 'chapter-1')
    expect(wrapper.text()).toContain('剧情轨道')
    expect(wrapper.text()).toContain('这里记录整部小说的大方向，可随时修改；保存后供章节规划和写作辅助参考。')
    expect(wrapper.text()).not.toContain('content_text')
    expect(wrapper.text()).not.toContain('派生缓存')
    expect(wrapper.text()).toContain('当前阶段：追查旧地图')
    expect(wrapper.text()).toContain('终局目标：揭开海雾秘密')
    expect(wrapper.text()).toContain('灯塔迷局')
    expect(wrapper.text()).toContain('确认灯塔背后的势力')
    expect(wrapper.text()).toContain('完成第一轮追索')
    expect(wrapper.text()).toContain('发现旧地图')
  })

  it('keeps the formal outline editor before collapsed AI references and truncates abnormal summaries', async () => {
    const abnormalSummary = `错误分析${'重复内容'.repeat(100)}`
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '这是用户导入并保存的正式作品大纲',
      content_tree_json: [],
      version: 1
    })
    mockGetContextPackReadiness.mockResolvedValue({
      data: {
        status: 'degraded',
        plot_arc_statuses: { master_arc: { status: 'degraded' } },
        plot_arc_summary: {
          master_arc: {
            arc_title: '系统整理结果',
            current_stage: abnormalSummary,
            ultimate_goal: abnormalSummary
          },
          volume_arc: { stage_goal: abnormalSummary },
          sequence_arc: { sequence_goal: abnormalSummary, key_events: [abnormalSummary] }
        }
      }
    })

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1', activeChapterId: 'chapter-1' }
    })
    await flushPromises()

    const editor = wrapper.get('.outline-editor-shell').element
    const aiReference = wrapper.get('[data-testid="plot-arc-reference"]').element
    expect(editor.compareDocumentPosition(aiReference) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(wrapper.get('[data-testid="work-outline-text"]').element.value).toBe('这是用户导入并保存的正式作品大纲')
    expect(wrapper.get('[data-testid="plot-arc-reference"]').attributes('open')).toBeUndefined()
    expect(wrapper.text()).toContain('不会修改作品大纲或章节大纲')
    expect(wrapper.text()).not.toContain(abnormalSummary)
  })

  it('imports outline content into work draft with replace mode and does not call save api', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '远端大纲',
      content_tree_json: [],
      version: 3
    })

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.get('[data-testid="outline-import-trigger"]').trigger('click')
    wrapper.getComponent({ name: 'OutlineImportModal' }).vm.$emit('import', {
      content: '导入作品大纲',
      mode: 'replace'
    })
    await flushPromises()

    const store = useWritingAssetStore()
    expect(wrapper.find('[data-testid="work-outline-text"]').element.value).toBe('导入作品大纲')
    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '导入作品大纲',
        expected_version: 3
      }
    })
    expect(localCache.get('asset_draft:work_outline:work-1')).toMatchObject({
      payload: {
        content_text: '导入作品大纲'
      }
    })
    expect(mockSaveWorkOutline).not.toHaveBeenCalled()
  })

  it('appends imported text with blank line separator when work draft already has content', async () => {
    mockGetWorkOutline.mockResolvedValue({
      id: 'outline-1',
      work_id: 'work-1',
      content_text: '原始大纲',
      content_tree_json: [],
      version: 2
    })

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.get('[data-testid="outline-import-trigger"]').trigger('click')
    wrapper.getComponent({ name: 'OutlineImportModal' }).vm.$emit('import', {
      content: '追加内容',
      mode: 'append'
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="work-outline-text"]').element.value).toBe('原始大纲\n\n追加内容')
  })

  it('saves imported work outline with expected_version and clears local draft', async () => {
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
      content_text: '已保存导入大纲',
      content_tree_json: [],
      version: 2
    })

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    wrapper.getComponent({ name: 'OutlineImportModal' }).vm.$emit('import', {
      content: '已保存导入大纲',
      mode: 'replace'
    })
    await flushPromises()

    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockSaveWorkOutline).toHaveBeenCalledWith('work-1', {
      content_text: '已保存导入大纲',
      content_tree_json: [],
      expected_version: 1
    })
    expect(useWritingAssetStore().assetDrafts['work_outline:work']).toBeUndefined()
    expect(localCache.get('asset_draft:work_outline:work-1')).toBeNull()
  })

  it('keeps imported local draft and opens conflict modal after 409', async () => {
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
      resource_id: 'outline-1',
      server_content: '服务端大纲'
    }
    mockSaveWorkOutline.mockRejectedValue(conflictError)

    const wrapper = mount(OutlinePanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    wrapper.getComponent({ name: 'OutlineImportModal' }).vm.$emit('import', {
      content: '冲突导入大纲',
      mode: 'replace'
    })
    await flushPromises()
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(store.assetDrafts['work_outline:work']).toMatchObject({
      payload: {
        content_text: '冲突导入大纲'
      }
    })
    expect(localCache.get('asset_draft:work_outline:work-1')).toMatchObject({
      payload: {
        content_text: '冲突导入大纲'
      }
    })
    expect(wrapper.findComponent({ name: 'AssetConflictModal' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('资料版本冲突')
  })

  it('switches to chapter mode and keeps chapter outline save path independent', async () => {
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
    expect(wrapper.find('[data-testid="outline-import-trigger"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="chapter-outline-text"]').element.value).toBe('远端章节细纲')

    await wrapper.find('[data-testid="chapter-outline-text"]').setValue('章节细纲草稿')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockSaveChapterOutline).toHaveBeenCalledWith('chapter-1', {
      content_text: '章节细纲草稿',
      content_tree_json: [],
      expected_version: 4
    })
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
})
