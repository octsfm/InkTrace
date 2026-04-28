import { createPinia, setActivePinia } from 'pinia'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

import NovelWorkspace from '../NovelWorkspace.vue'
import { useChapterDataStore } from '@/stores/useChapterDataStore'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { useSaveStateStore } from '@/stores/useSaveStateStore'

const mockPush = vi.fn()
const mockListChapters = vi.fn()
const mockCreateChapter = vi.fn()
const mockUpdateChapter = vi.fn()
const mockForceOverrideChapter = vi.fn()
const mockDeleteChapter = vi.fn()
const mockReorderChapters = vi.fn()
const mockGetSession = vi.fn()
const mockSaveSession = vi.fn()
const mockLocalCacheGet = vi.fn()
const mockLocalCacheKeys = vi.fn()
const mockLocalCacheSet = vi.fn()
const mockLocalCacheRemove = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      id: 'work-1'
    }
  }),
  useRouter: () => ({
    push: mockPush
  })
}))

vi.mock('@/api', () => ({
  v1ChaptersApi: {
    list: (...args) => mockListChapters(...args),
    create: (...args) => mockCreateChapter(...args),
    update: (...args) => mockUpdateChapter(...args),
    forceOverride: (...args) => mockForceOverrideChapter(...args),
    delete: (...args) => mockDeleteChapter(...args),
    reorder: (...args) => mockReorderChapters(...args)
  },
  v1SessionsApi: {
    get: (...args) => mockGetSession(...args),
    save: (...args) => mockSaveSession(...args)
  }
}))

vi.mock('@/utils/localCache', () => ({
  localCache: {
    get: (...args) => mockLocalCacheGet(...args),
    keys: (...args) => mockLocalCacheKeys(...args),
    set: (...args) => mockLocalCacheSet(...args),
    remove: (...args) => mockLocalCacheRemove(...args)
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() }
}))

enableAutoUnmount(afterEach)

describe('NovelWorkspace', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback) => {
      callback()
      return 1
    })
    setActivePinia(createPinia())
    mockPush.mockReset()
    mockListChapters.mockReset()
    mockCreateChapter.mockReset()
    mockUpdateChapter.mockReset()
    mockForceOverrideChapter.mockReset()
    mockDeleteChapter.mockReset()
    mockReorderChapters.mockReset()
    mockGetSession.mockReset()
    mockSaveSession.mockReset()
    mockLocalCacheGet.mockReset()
    mockLocalCacheKeys.mockReset()
    mockLocalCacheSet.mockReset()
    mockLocalCacheRemove.mockReset()
    ElMessage.success.mockReset()
    ElMessage.warning.mockReset()
    ElMessage.error.mockReset()
    mockListChapters.mockResolvedValue([
      { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 },
      { id: 'ch-2', title: '第二章', content: '第二章内容', word_count: 1600, version: 2 }
    ])
    mockCreateChapter.mockResolvedValue({
      id: 'ch-3',
      title: '',
      content: '',
      word_count: 0,
      version: 1,
      updated_at: '2026-04-28T18:00:04.000Z'
    })
    mockUpdateChapter.mockImplementation(async (chapterId, payload) => ({
      id: chapterId,
      title: payload.title ?? (chapterId === 'ch-1' ? '第一章' : '第二章'),
      content: payload.content ?? (chapterId === 'ch-1' ? '第一章内容' : '第二章内容'),
      word_count: String(payload.content ?? (chapterId === 'ch-1' ? '第一章内容' : '第二章内容')).length,
      version: chapterId === 'ch-1' ? 2 : 3,
      updated_at: '2026-04-28T18:00:02.000Z'
    }))
    mockForceOverrideChapter.mockImplementation(async (chapterId, payload) => ({
      id: chapterId,
      title: chapterId === 'ch-1' ? '第一章' : '第二章',
      content: payload.content,
      word_count: String(payload.content || '').length,
      version: chapterId === 'ch-1' ? 2 : 3,
      updated_at: '2026-04-28T18:00:03.000Z'
    }))
    mockDeleteChapter.mockResolvedValue({
      ok: true,
      id: 'ch-2',
      next_chapter_id: 'ch-1'
    })
    mockReorderChapters.mockImplementation(async (workId, chapterIds) => ({
      work_id: workId,
      items: chapterIds.map((id, index) => ({
        id,
        title: id === 'ch-1' ? '第一章' : id === 'ch-2' ? '第二章' : '第三章',
        content: id === 'ch-1' ? '第一章内容' : id === 'ch-2' ? '第二章内容' : '',
        word_count: id === 'ch-1' ? 1200 : id === 'ch-2' ? 1600 : 0,
        version: index + 1,
        order_index: index + 1
      })),
      total: chapterIds.length
    }))
    mockGetSession.mockResolvedValue({
      last_open_chapter_id: 'ch-2',
      cursor_position: 3,
      scroll_top: 0,
      updated_at: '2026-04-28T18:00:00.000Z'
    })
    mockSaveSession.mockResolvedValue({
      updated_at: '2026-04-28T18:00:01.000Z'
    })
    mockLocalCacheGet.mockReturnValue(null)
    mockLocalCacheKeys.mockReturnValue([])
    vi.stubGlobal('navigator', {
      onLine: true
    })
    vi.stubGlobal('confirm', vi.fn(() => true))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('renders three-column writing studio skeleton', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    expect(wrapper.text()).toContain('纯文本写作页')
    expect(wrapper.text()).toContain('章节列表')
    expect(wrapper.text()).toContain('编辑区')
    expect(wrapper.text()).toContain('右侧面板在 V1 默认隐藏')
    expect(wrapper.text()).toContain('第一章')
    expect(wrapper.text()).toContain('第二章')
    expect(wrapper.text()).toContain('已同步')
    expect(wrapper.text()).toContain('本章字数 5')
    expect(wrapper.text()).toContain('会话已加载')
    expect(wrapper.find('textarea').element.value).toBe('第二章内容')
    expect(wrapper.find('.studio-shell').exists()).toBe(true)
  })

  it('navigates back to works list', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const button = wrapper.findAll('button').find((node) => node.text().includes('返回书架'))
    expect(button).toBeTruthy()
    await button.trigger('click')

    expect(mockPush).toHaveBeenCalledWith('/works')
  })

  it('shows an error message when chapters fail to load', async () => {
    mockListChapters.mockRejectedValueOnce(new Error('load failed'))
    mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()

    expect(ElMessage.error).toHaveBeenCalledWith('章节列表加载失败，请稍后重试。')
  })

  it('syncs editor draft and viewport state into stores', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const chapterDataStore = useChapterDataStore()
    const workspaceStore = useWorkspaceStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('新的正文')
    textarea.element.selectionStart = 4
    await textarea.trigger('click')
    textarea.element.scrollTop = 88
    await textarea.trigger('scroll')

    expect(chapterDataStore.draftByChapterId['ch-2']).toBe('新的正文')
    expect(workspaceStore.lastOpenChapterId).toBe('ch-2')
    expect(workspaceStore.cursorPosition).toBe(4)
    expect(workspaceStore.scrollTop).toBe(88)
  })

  it('creates a chapter after the active chapter and activates it', async () => {
    mockListChapters
      .mockResolvedValueOnce([
        { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 },
        { id: 'ch-2', title: '第二章', content: '第二章内容', word_count: 1600, version: 2 }
      ])
      .mockResolvedValueOnce([
        { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 },
        { id: 'ch-2', title: '第二章', content: '第二章内容', word_count: 1600, version: 2 },
        { id: 'ch-3', title: '', content: '', word_count: 0, version: 1 }
      ])

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    await wrapper.find('.add-button').trigger('click')
    await flushPromises()

    expect(mockCreateChapter).toHaveBeenCalledWith('work-1', {
      title: '',
      after_chapter_id: 'ch-2'
    })
    expect(wrapper.find('textarea').element.value).toBe('')
    expect(ElMessage.success).toHaveBeenCalledWith('已新建章节。')
  })

  it('renames chapter from sidebar and updates the list', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const firstItem = wrapper.findAll('.chapter-item')[0]
    await firstItem.find('.chapter-action-button').trigger('click')
    const input = firstItem.find('.chapter-rename-input')
    await input.setValue('第一章·修订')
    await input.trigger('blur')
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledWith('ch-1', {
      title: '第一章·修订',
      expected_version: 1
    })
    expect(wrapper.text()).toContain('第一章·修订')
  })

  it('deletes chapter from sidebar and falls back to the next focus', async () => {
    mockListChapters
      .mockResolvedValueOnce([
        { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 },
        { id: 'ch-2', title: '第二章', content: '第二章内容', word_count: 1600, version: 2 }
      ])
      .mockResolvedValueOnce([
        { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 }
      ])

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const activeItem = wrapper.findAll('.chapter-item')[1]
    await activeItem.find('.chapter-action-button.danger').trigger('click')
    await flushPromises()

    expect(mockDeleteChapter).toHaveBeenCalledWith('ch-2')
    expect(wrapper.find('textarea').element.value).toBe('第一章内容')
    expect(ElMessage.success).toHaveBeenCalledWith('章节已删除。')
  })

  it('reorders chapters from sidebar drag and drop', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const items = wrapper.findAll('.chapter-item')
    const dataTransfer = {
      setData: () => {},
      effectAllowed: 'move'
    }

    await items[1].trigger('dragstart', { dataTransfer })
    await items[0].trigger('dragover', {
      preventDefault: () => {}
    })
    await items[0].trigger('drop')
    await flushPromises()

    expect(mockReorderChapters).toHaveBeenCalledWith('work-1', ['ch-2', 'ch-1'])
    expect(wrapper.findAll('.chapter-title')[0].text()).toContain('第二章')
  })

  it('updates status bar when save state changes', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    saveStateStore.markSaving()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('保存中...')

    saveStateStore.markOffline()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('离线模式：当前网络离线，编辑仍可继续。')
    expect(wrapper.text()).toContain('已同步')
  })

  it('shows soft limit warning for chapters over 200000 effective characters', async () => {
    mockListChapters.mockResolvedValueOnce([
      {
        id: 'ch-1',
        title: '第一章',
        content: '第一章内容',
        word_count: 1200,
        version: 1
      },
      {
        id: 'ch-2',
        title: '第二章',
        content: `${'字'.repeat(200000)} \n\t字`,
        word_count: 200001,
        version: 2
      }
    ])

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    expect(wrapper.text()).toContain('当前章节已超过 20 万有效字符')
    expect(wrapper.text()).toContain('本章字数 200,001')
    expect(wrapper.find('textarea').element.value.length).toBe(200004)
  })

  it('blocks chapter switching while saving and switches after save completes', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const chapterDataStore = useChapterDataStore()
    const saveStateStore = useSaveStateStore()

    saveStateStore.markSaving()
    await wrapper.findAll('.chapter-select-button')[0].trigger('click')

    expect(chapterDataStore.activeChapterId).toBe('ch-2')
    expect(ElMessage.warning).toHaveBeenCalledWith('正在同步数据，请稍候...')

    saveStateStore.markSynced('2026-04-28T16:00:00.000Z')
    await wrapper.vm.$nextTick()

    expect(chapterDataStore.activeChapterId).toBe('ch-1')
  })

  it('restores chapter from session and persists session after viewport changes', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const workspaceStore = useWorkspaceStore()
    const chapterDataStore = useChapterDataStore()
    const textarea = wrapper.find('textarea')

    expect(mockGetSession).toHaveBeenCalledWith('work-1')
    expect(chapterDataStore.activeChapterId).toBe('ch-2')
    expect(workspaceStore.cursorPosition).toBe(3)

    await textarea.setValue('第二章修订')
    textarea.element.selectionStart = 5
    await textarea.trigger('click')
    textarea.element.scrollTop = 64
    await textarea.trigger('scroll')
    await vi.advanceTimersByTimeAsync(801)
    await flushPromises()

    expect(mockSaveSession).toHaveBeenCalledWith('work-1', {
      chapter_id: 'ch-2',
      cursor_position: 5,
      scroll_top: 64
    })
    expect(workspaceStore.sessionUpdatedAt).toBe('2026-04-28T18:00:01.000Z')
  })

  it('writes local cache immediately and clears it after chapter sync succeeds', async () => {
    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const chapterDataStore = useChapterDataStore()
    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('本地优先正文')

    expect(mockLocalCacheSet).toHaveBeenCalled()
    expect(saveStateStore.saveStatus).toBe('saving')

    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledWith('ch-2', {
      content: '本地优先正文',
      expected_version: 2
    })
    expect(mockLocalCacheRemove).toHaveBeenCalledWith('draft:work-1:ch-2')
    expect(chapterDataStore.draftByChapterId['ch-2']).toBeUndefined()
    expect(saveStateStore.saveStatus).toBe('synced')
  })

  it('keeps over-limit chapter editable and saves it successfully', async () => {
    mockListChapters.mockResolvedValueOnce([
      { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 },
      {
        id: 'ch-2',
        title: '第二章',
        content: `${'字'.repeat(200000)} \n\t字`,
        word_count: 200001,
        version: 2
      }
    ])

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')
    const nextContent = `${'字'.repeat(200000)}继续写完`

    await textarea.setValue(nextContent)

    expect(wrapper.text()).toContain('当前章节已超过 20 万有效字符')
    expect(saveStateStore.saveStatus).toBe('saving')

    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenLastCalledWith('ch-2', {
      content: nextContent,
      expected_version: 2
    })
    expect(saveStateStore.saveStatus).toBe('synced')
    expect(wrapper.text()).toContain('已同步')
  })

  it('still switches chapter after saving an over-limit draft', async () => {
    mockListChapters.mockResolvedValueOnce([
      { id: 'ch-1', title: '第一章', content: '第一章内容', word_count: 1200, version: 1 },
      {
        id: 'ch-2',
        title: '第二章',
        content: `${'字'.repeat(200000)}额外内容`,
        word_count: 200004,
        version: 2
      }
    ])

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const chapterDataStore = useChapterDataStore()
    const overLimitContent = `${'字'.repeat(200001)}继续`
    const textarea = wrapper.find('textarea')

    await textarea.setValue(overLimitContent)
    await wrapper.findAll('.chapter-select-button')[0].trigger('click')

    expect(chapterDataStore.activeChapterId).toBe('ch-2')
    expect(wrapper.text()).toContain('当前章节已超过 20 万有效字符')

    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenLastCalledWith('ch-2', {
      content: overLimitContent,
      expected_version: 2
    })
    expect(chapterDataStore.activeChapterId).toBe('ch-1')
    expect(wrapper.find('textarea').element.value).toBe('第一章内容')
  })

  it('restores cached local draft after reload', async () => {
    mockLocalCacheGet.mockImplementation((key) => {
      if (key === 'draft:work-1:ch-2') {
        return {
          content: '缓存中的正文',
          cursorPosition: 9,
          scrollTop: 70
        }
      }
      return null
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const workspaceStore = useWorkspaceStore()

    expect(wrapper.find('textarea').element.value).toBe('缓存中的正文')
    expect(workspaceStore.cursorPosition).toBe(6)
    expect(workspaceStore.scrollTop).toBe(0)
    expect(mockLocalCacheGet).toHaveBeenCalledWith('draft:work-1:ch-2', null)
  })

  it('shows a blocking conflict modal when chapter sync returns 409', async () => {
    mockUpdateChapter.mockRejectedValueOnce({
      response: {
        status: 409
      },
      userMessage: 'Version conflict'
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('发生冲突的正文')
    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()

    expect(saveStateStore.saveStatus).toBe('error')
    expect(wrapper.text()).toContain('检测到版本冲突')
    expect(wrapper.text()).toContain('强制覆盖云端')
    expect(wrapper.text()).toContain('放弃本地修改，重新加载云端')
    expect(mockLocalCacheRemove).not.toHaveBeenCalledWith('draft:work-1:ch-2')
  })

  it('discards local draft and reloads cloud content after conflict decision', async () => {
    mockUpdateChapter.mockRejectedValueOnce({
      response: {
        status: 409
      },
      userMessage: 'Version conflict'
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const chapterDataStore = useChapterDataStore()
    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('需要放弃的正文')
    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()
    await wrapper.find('button.ghost-button').trigger('click')
    await flushPromises()

    expect(mockListChapters).toHaveBeenCalledTimes(2)
    expect(chapterDataStore.draftByChapterId['ch-2']).toBeUndefined()
    expect(wrapper.find('textarea').element.value).toBe('第二章内容')
    expect(saveStateStore.saveStatus).toBe('synced')
    expect(mockLocalCacheRemove).toHaveBeenCalledWith('draft:work-1:ch-2')
    expect(ElMessage.success).toHaveBeenCalledWith('已放弃本地修改，并重新加载云端内容。')
  })

  it('forces override with local content after conflict decision', async () => {
    mockUpdateChapter.mockRejectedValueOnce({
      response: {
        status: 409
      },
      userMessage: 'Version conflict'
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const chapterDataStore = useChapterDataStore()
    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('用于覆盖的本地正文')
    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()
    await wrapper.find('button.danger-button').trigger('click')
    await flushPromises()

    expect(mockForceOverrideChapter).toHaveBeenLastCalledWith('ch-2', {
      content: '用于覆盖的本地正文',
      expected_version: 2
    })
    expect(chapterDataStore.draftByChapterId['ch-2']).toBeUndefined()
    expect(saveStateStore.saveStatus).toBe('synced')
    expect(wrapper.text()).not.toContain('检测到版本冲突')
    expect(mockLocalCacheRemove).toHaveBeenCalledWith('draft:work-1:ch-2')
    expect(ElMessage.success).toHaveBeenCalledWith('已使用本地内容覆盖云端版本。')
  })

  it('retries chapter save with exponential backoff and succeeds before limit', async () => {
    mockUpdateChapter
      .mockRejectedValueOnce({
        response: { status: 500 },
        userMessage: 'server error'
      })
      .mockRejectedValueOnce({
        response: { status: 500 },
        userMessage: 'server error'
      })
      .mockResolvedValueOnce({
        id: 'ch-2',
        title: '第二章',
        content: '重试成功正文',
        word_count: 6,
        version: 3,
        updated_at: '2026-04-28T18:00:05.000Z'
      })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('重试成功正文')
    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledTimes(1)
    expect(saveStateStore.saveStatus).toBe('error')
    expect(saveStateStore.retryCount).toBe(1)
    expect(saveStateStore.nextRetryAt).not.toBe('')

    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledTimes(2)
    expect(saveStateStore.retryCount).toBe(2)

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledTimes(3)
    expect(saveStateStore.saveStatus).toBe('synced')
    expect(saveStateStore.retryCount).toBe(0)
    expect(saveStateStore.nextRetryAt).toBe('')
  })

  it('shows manual retry after reaching retry limit', async () => {
    let attempt = 0
    mockUpdateChapter.mockImplementation(async () => {
      attempt += 1
      if (attempt <= 4) {
        throw {
          response: { status: 500 },
          userMessage: 'server error'
        }
      }
      return {
        id: 'ch-2',
        title: '第二章',
        content: '手动重试成功',
        word_count: 6,
        version: 3,
        updated_at: '2026-04-28T18:00:06.000Z'
      }
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    const textarea = wrapper.find('textarea')

    await textarea.setValue('手动重试成功')
    await vi.advanceTimersByTimeAsync(2501)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledTimes(4)
    expect(saveStateStore.saveStatus).toBe('error')
    expect(saveStateStore.retryCount).toBe(3)
    expect(saveStateStore.nextRetryAt).toBe('')
    expect(wrapper.text()).toContain('手动重试')

    await wrapper.find('.retry-button').trigger('click')
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenCalledTimes(5)
    expect(saveStateStore.saveStatus).toBe('synced')
    expect(saveStateStore.retryCount).toBe(0)
    expect(ElMessage.success).not.toHaveBeenCalledWith('已使用本地内容覆盖云端版本。')
  })

  it('hydrates cached drafts into offline replay queue on mount', async () => {
    vi.stubGlobal('navigator', {
      onLine: false
    })
    mockLocalCacheGet.mockImplementation((key) => {
      if (key === 'draft:work-1:ch-1') {
        return {
          chapterId: 'ch-1',
          content: '第一章离线草稿',
          timestamp: 100
        }
      }
      if (key === 'draft:work-1:ch-2') {
        return {
          chapterId: 'ch-2',
          content: '第二章离线草稿',
          timestamp: 200
        }
      }
      return null
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()

    expect(saveStateStore.saveStatus).toBe('offline')
    expect(saveStateStore.pendingQueue.map((item) => item.chapterId)).toEqual(['ch-1', 'ch-2'])
    expect(wrapper.find('textarea').element.value).toBe('第二章离线草稿')
    expect(wrapper.text()).toContain('离线积压 2 条草稿')
    expect(wrapper.text()).toContain('同步失败')
  })

  it('replays offline drafts in timestamp order after network resumes', async () => {
    vi.stubGlobal('navigator', {
      onLine: false
    })
    mockLocalCacheKeys.mockReturnValue([
      'draft:work-1:ch-2',
      'draft:work-1:ch-1'
    ])
    mockLocalCacheGet.mockImplementation((key) => {
      if (key === 'draft:work-1:ch-1') {
        return {
          chapterId: 'ch-1',
          content: '较早草稿',
          timestamp: 100
        }
      }
      if (key === 'draft:work-1:ch-2') {
        return {
          chapterId: 'ch-2',
          content: '较晚草稿',
          timestamp: 200
        }
      }
      return null
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    expect(saveStateStore.pendingQueue.map((item) => item.chapterId)).toEqual(['ch-1', 'ch-2'])

    globalThis.navigator.onLine = true
    window.dispatchEvent(new Event('online'))
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    expect(mockUpdateChapter).toHaveBeenNthCalledWith(1, 'ch-1', {
      content: '较早草稿',
      expected_version: 1
    })
    expect(mockUpdateChapter).toHaveBeenNthCalledWith(2, 'ch-2', {
      content: '较晚草稿',
      expected_version: 2
    })
    expect(mockLocalCacheRemove).toHaveBeenCalledWith('draft:work-1:ch-1')
    expect(mockLocalCacheRemove).toHaveBeenCalledWith('draft:work-1:ch-2')
    expect(saveStateStore.pendingQueue).toEqual([])
    expect(saveStateStore.saveStatus).toBe('synced')
    expect(wrapper.text()).toContain('已同步')
  })

  it('returns to synced after browser goes online with no pending offline drafts', async () => {
    vi.stubGlobal('navigator', {
      onLine: false
    })

    const wrapper = mount(NovelWorkspace, {
      global: {
        stubs: {
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
        }
      }
    })
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    const saveStateStore = useSaveStateStore()
    expect(saveStateStore.saveStatus).toBe('offline')
    expect(wrapper.text()).toContain('离线模式：当前网络离线，编辑仍可继续。')

    globalThis.navigator.onLine = true
    window.dispatchEvent(new Event('online'))
    await flushPromises()
    await vi.runAllTimersAsync()
    await flushPromises()

    expect(saveStateStore.saveStatus).toBe('synced')
    expect(wrapper.text()).toContain('已同步')
    expect(wrapper.text()).not.toContain('离线模式：当前网络离线，编辑仍可继续。')
  })
})
