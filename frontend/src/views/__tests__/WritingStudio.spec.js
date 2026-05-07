import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useChapterDataStore } from '@/stores/useChapterDataStore'
import { usePreferenceStore } from '@/stores/preference'

const routerPush = vi.fn()
const mockV1WorksGet = vi.fn()
const mockV1WorksUpdate = vi.fn()
const mockV1ChaptersList = vi.fn()
const mockV1ChaptersUpdate = vi.fn()
const mockV1ChaptersCreate = vi.fn()
const mockV1ChaptersDelete = vi.fn()
const mockV1ChaptersReorder = vi.fn()
const mockV1ChaptersForceOverride = vi.fn()
const mockV1SessionsGet = vi.fn()
const mockV1SessionsSave = vi.fn()
const elMessage = {
  warning: vi.fn(),
  error: vi.fn(),
  success: vi.fn()
}

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      id: 'work-1'
    }
  }),
  useRouter: () => ({
    push: routerPush
  })
}))

vi.mock('element-plus', () => ({
  ElMessage: elMessage
}))

vi.mock('@/api', () => ({
  v1WorksApi: {
    get: mockV1WorksGet,
    update: mockV1WorksUpdate
  },
  v1ChaptersApi: {
    list: mockV1ChaptersList,
    update: mockV1ChaptersUpdate,
    create: mockV1ChaptersCreate,
    delete: mockV1ChaptersDelete,
    reorder: mockV1ChaptersReorder,
    forceOverride: mockV1ChaptersForceOverride
  },
  v1SessionsApi: {
    get: mockV1SessionsGet,
    save: mockV1SessionsSave
  }
}))

const source = readFileSync(resolve(process.cwd(), 'src/views/WritingStudio.vue'), 'utf8')

const ChapterSidebarStub = defineComponent({
  name: 'ChapterSidebarStub',
  setup(_, { expose }) {
    expose({
      scrollToChapter: vi.fn()
    })
    return () => h('div', { class: 'chapter-sidebar-stub' })
  }
})

const ChapterTitleInputStub = defineComponent({
  name: 'ChapterTitleInputStub',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      class: 'chapter-title-input-stub',
      value: props.modelValue,
      onInput: (event) => emit('update:modelValue', event.target.value)
    })
  }
})

const AssetRailStub = defineComponent({
  name: 'AssetRailStub',
  setup() {
    return () => h('div', { class: 'asset-rail-stub' })
  }
})

const AssetDrawerStub = defineComponent({
  name: 'AssetDrawerStub',
  props: {
    activeTab: {
      type: String,
      default: ''
    }
  },
  setup(props, { slots }) {
    return () => h('div', { class: 'asset-drawer-body' }, slots.default?.({ activeTab: props.activeTab }) || [])
  }
})

const buildAssetPanelStub = (className) => defineComponent({
  name: `${className}Stub`,
  setup(_, { expose }) {
    expose({
      saveFocusedDraft: vi.fn(async () => {}),
      discardFocusedDraft: vi.fn()
    })
    return () => h('div', { class: `${className}-stub` })
  }
})

const StatusBarStub = defineComponent({
  name: 'StatusBarStub',
  setup() {
    return () => h('div', { class: 'status-bar-stub' }, '状态栏')
  }
})

const VersionConflictModalStub = defineComponent({
  name: 'VersionConflictModalStub',
  setup() {
    return () => h('div', { class: 'version-conflict-modal-stub' })
  }
})

const createPureTextEditorStub = ({
  getViewportSpy = vi.fn(),
  restoreViewportSpy = vi.fn(),
  focusEditorSpy = vi.fn()
} = {}) => defineComponent({
  name: 'PureTextEditorStub',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  setup(props, { expose }) {
    const textareaRef = ref(null)

    const readViewport = () => ({
      cursorPosition: Number(textareaRef.value?.selectionStart || 0),
      scrollTop: Number(textareaRef.value?.scrollTop || 0)
    })

    const getViewport = () => {
      const viewport = readViewport()
      getViewportSpy(viewport)
      return viewport
    }

    const restoreViewport = ({ cursorPosition = 0, scrollTop = 0 } = {}) => {
      restoreViewportSpy({
        cursorPosition: Number(cursorPosition || 0),
        scrollTop: Number(scrollTop || 0)
      })
      if (!textareaRef.value) return
      textareaRef.value.selectionStart = Number(cursorPosition || 0)
      textareaRef.value.selectionEnd = Number(cursorPosition || 0)
      textareaRef.value.scrollTop = Number(scrollTop || 0)
    }

    const focusEditor = () => {
      focusEditorSpy()
      textareaRef.value?.focus()
    }

    expose({
      getViewport,
      restoreViewport,
      focusEditor
    })

    return () => h('textarea', {
      ref: textareaRef,
      class: 'pure-text-editor-stub',
      value: props.modelValue
    }, props.modelValue)
  }
})

const flushStudio = async () => {
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

describe('WritingStudio layout contract', () => {
  it('mounts the required writing studio regions and workspace components', () => {
    expect(source).toContain('class="studio-shell"')
    expect(source).toContain('class="sidebar-column"')
    expect(source).toContain('class="editor-column"')
    expect(source).toContain('class="asset-rail-column"')
    expect(source).toContain('<ChapterSidebar')
    expect(source).toContain('<ChapterTitleInput')
    expect(source).toContain('<PureTextEditor')
    expect(source).toContain('<AssetRail')
    expect(source).toContain('<AssetDrawer')
  })

  it('initializes work and session through workspace store while loading chapters from v1 API', () => {
    expect(source).toContain('workspaceStore.initializeWorkspace(workId.value)')
    expect(source).toContain('loadChapters()')
    expect(source).toContain('activateChapter(initialChapterId)')
  })

  it('focuses the pure text editor after the initial chapter is activated', () => {
    expect(source).toContain('await activateChapter(initialChapterId)')
    expect(source).toContain('await focusEditor()')
  })

  it('keeps AssetDrawer as a single active drawer controlled by activeAssetTab', () => {
    expect(source).toContain('const activeAssetTab = ref')
    expect(source).toContain('v-if="activeAssetTab"')
    expect(source).toContain(':active-tab="activeAssetTab"')
    expect(source).toContain(':hide-active-entry="Boolean(activeAssetTab)"')
    expect(source).toContain(':mobile="isMobileAssetDrawer"')
    expect(source).toContain('toggleAssetDrawer')
    expect(source).toContain('closeAssetDrawer')
  })

  it('uses mobile overlay wiring for asset drawer without creating a separate page', () => {
    expect(source).toContain('const MOBILE_ASSET_BREAKPOINT = 760')
    expect(source).toContain('const isMobileAssetDrawer = ref(false)')
    expect(source).toContain('const syncAssetDrawerViewport = () =>')
    expect(source).toContain("window.addEventListener('resize', syncAssetDrawerViewport)")
    expect(source).toContain("window.removeEventListener('resize', syncAssetDrawerViewport)")
    expect(source).toContain(":class=\"{ 'mobile-overlay-host': isMobileAssetDrawer }\"")
    expect(source).toContain('.asset-drawer-column.mobile-overlay-host')
    expect(source).not.toContain("router.push('/assets'")
  })

  it('mounts outline timeline and foreshadow asset panels inside the drawer', () => {
    expect(source).toContain('<OutlinePanel')
    expect(source).toContain('<TimelinePanel')
    expect(source).toContain('<ForeshadowPanel')
    expect(source).toContain('<CharacterPanel')
    expect(source).not.toContain('outline_file')
    expect(source).not.toContain('导入大纲')
  })

  it('defines header title editing and rename behavior without exposing work id', () => {
    expect(source).toContain('class="work-title-button"')
    expect(source).toContain('@click="startWorkTitleEditing"')
    expect(source).toContain('class="work-title-input"')
    expect(source).toContain('@keydown.enter.prevent="submitWorkTitleEditing"')
    expect(source).toContain('@keydown.esc.prevent="cancelWorkTitleEditing"')
    expect(source).toContain('v1WorksApi.update(workId.value, { title: nextTitle })')
    expect(source).not.toContain('{{ workId }}')
  })

  it('restores editor focus after header title submit or cancel', () => {
    expect(source).toContain('const cancelWorkTitleEditing = async')
    expect(source).toContain('await focusEditor()')
    expect(source).toContain('finally {')
  })

  it('routes Ctrl/Cmd+S from the focused editor to immediate chapter flush', () => {
    expect(source).toContain('window.addEventListener(\'keydown\', handleEditorSaveShortcut)')
    expect(source).toContain('key !== \'s\'')
    expect(source).toContain('activeElement?.closest?.(\'.editor-shell\')')
    expect(source).toContain('activeElement?.closest?.(\'.asset-drawer-body\')')
    expect(source).toContain('event.preventDefault()')
    expect(source).toContain('await flushCurrentDraftNow()')
  })

  it('routes Ctrl/Cmd+S inside asset drawer only to the focused asset panel', () => {
    expect(source).toContain('const saveFocusedAssetDraft = async')
    expect(source).toContain("if (activeAssetTab.value === 'outline')")
    expect(source).toContain('outlinePanelRef.value?.saveFocusedDraft?.(activeAssetFocusArea.value)')
    expect(source).toContain("if (activeAssetTab.value === 'timeline')")
    expect(source).toContain("activeAssetFocusArea.value === 'timeline_reorder' ? 'reorder' : 'event'")
    expect(source).toContain('timelinePanelRef.value?.saveFocusedDraft?.(mode)')
    expect(source).toContain("if (activeAssetTab.value === 'foreshadow')")
    expect(source).toContain('foreshadowPanelRef.value?.saveFocusedDraft?.()')
    expect(source).toContain("if (activeAssetTab.value === 'character')")
    expect(source).toContain('characterPanelRef.value?.saveFocusedDraft?.()')
    expect(source).not.toContain("activeElement?.closest?.('.asset-rail-column')")
  })

  it('uses save state store as the local draft boundary', () => {
    expect(source).toContain('saveStateStore.readLocalDraft')
    expect(source).toContain('saveStateStore.writeLocalDraft')
    expect(source).toContain('saveStateStore.clearLocalDraft')
    expect(source).toContain('saveStateStore.collectLocalDrafts')
    expect(source).not.toContain("from '@/utils/localCache'")
  })

  it('keeps offline writing visible and replays drafts automatically after network recovery', () => {
    expect(source).toContain(':offline="offlineBannerVisible"')
    expect(source).toContain(':offline-message="offlineBannerText"')
    expect(source).toContain("return '离线模式：修改已写入本地缓存，恢复联网后会自动同步。'")
    expect(source).toContain('const handleBrowserOffline = () =>')
    expect(source).toContain('const handleBrowserOnline = async () =>')
    expect(source).toContain('await replayOfflineDrafts()')
    expect(source).toContain("window.addEventListener('offline', handleBrowserOffline)")
    expect(source).toContain("window.addEventListener('online', handleBrowserOnline)")
  })

  it('does not auto-submit structured asset drafts on network recovery', () => {
    expect(source).toContain('const handleBrowserOnline = async () => {')
    expect(source).toContain('if (conflictModalVisible.value) return')
    expect(source).toContain('await replayOfflineDrafts()')
    expect(source).not.toContain('await assetStore.saveWorkOutline(')
    expect(source).not.toContain('await assetStore.saveChapterOutline(')
    expect(source).not.toContain('await assetStore.reorderTimelineEvents(')
    expect(source).not.toContain('await assetStore.updateForeshadow(')
    expect(source).not.toContain('await assetStore.updateCharacter(')
  })

  it('shows a cache prune warning when local cache evicts older drafts', () => {
    expect(source).toContain('const handleCachePruned = () =>')
    expect(source).toContain("ElMessage.warning('本地缓存空间不足，已自动清理较旧的暂存内容。')")
    expect(source).toContain("window.addEventListener('inktrace-cache-pruned', handleCachePruned)")
    expect(source).toContain("window.removeEventListener('inktrace-cache-pruned', handleCachePruned)")
  })

  it('wires full chapter conflict handling with cancel discard and override branches', () => {
    expect(source).toContain('<VersionConflictModal')
    expect(source).toContain('@cancel="handleConflictCancel"')
    expect(source).toContain('@discard="handleConflictDiscard"')
    expect(source).toContain('@override="handleConflictOverride"')
    expect(source).toContain('const handleConflictCancel = () =>')
    expect(source).toContain('const handleConflictDiscard = async () =>')
    expect(source).toContain('const handleConflictOverride = async () =>')
    expect(source).toContain('const conflictModalVisible = computed(() => saveStateStore.hasConflict)')
  })

  it('keeps local draft on cancel and clears it only after discard or override succeeds', () => {
    expect(source).toContain('// Keep the conflict payload and local draft untouched.')
    expect(source).toContain('chapterDataStore.clearChapterDraft(chapterId)')
    expect(source).toContain('chapterDataStore.clearChapterTitleDraft(chapterId)')
    expect(source).toContain('saveStateStore.removeDraft(chapterId)')
    expect(source).toContain('clearCachedDraft(chapterId)')
    expect(source).toContain('v1ChaptersApi.forceOverride(chapterId, {')
  })

  it('switches chapters after writing the current editor content to local cache without waiting for network saving', () => {
    expect(source).toContain('const handleSelectChapter = async')
    expect(source).toContain('writeCachedDraft(currentChapterId, chapterDataStore.activeChapterContent)')
    expect(source).toContain('await activateChapter(nextChapterId)')
    expect(source).toContain('await focusEditor()')
    expect(source).not.toContain("if (saveStateStore.saveStatus === 'saving') {\n    pendingChapterId.value = nextChapterId")
  })

  it('keeps long header titles truncated to one line', () => {
    expect(source).toContain('.work-title-button')
    expect(source).toContain('text-overflow: ellipsis')
    expect(source).toContain('white-space: nowrap')
    expect(source).toContain('overflow: hidden')
  })

  it('implements focus mode by reusing the local preference store and preserving the editor viewport', () => {
    expect(source).toContain("from '@/stores/preference'")
    expect(source).toContain('<FocusModeToggle')
    expect(source).toContain('const isFocusMode = computed(() => preferenceStore.focusMode)')
    expect(source).toContain('const captureActiveEditorViewport = () =>')
    expect(source).toContain('preferenceStore.toggleFocusMode()')
    expect(source).toContain('editorRef.value?.restoreViewport(preservedViewport)')
    expect(source).toContain('v-show="!isFocusMode"')
    expect(source).not.toContain('router.push(\'/focus\'')
  })

  it('wires a local writing preference panel without sending chapter save requests', () => {
    expect(source).toContain('<WritingPreferencePanel')
    expect(source).toContain('data-test="writing-preference-toggle"')
    expect(source).toContain('data-test="writing-preference-floating-panel"')
    expect(source).toContain('const preferencePanelVisible = ref(false)')
    expect(source).toContain('const closePreferencePanel = () =>')
    expect(source).toContain('document.addEventListener(\'pointerdown\', handlePreferencePanelPointerDown)')
    expect(source).toContain('window.addEventListener(\'keydown\', handlePreferencePanelEscape)')
    expect(source).toContain('const editorPreferences = computed(() => preferenceStore.editorPreferences)')
    expect(source).toContain('preferenceStore.updateWritingPreferences(patch)')
    expect(source).toContain(':font-family="editorPreferences.fontFamily"')
    expect(source).toContain(':font-size="editorPreferences.fontSize"')
    expect(source).toContain(':line-height="editorPreferences.lineHeight"')
    expect(source).toContain(':theme="editorPreferences.theme"')
  })

  it('tracks today word delta from正文有效字符变化 only', () => {
    expect(source).toContain(':today-word-delta="preferenceStore.todayWordDelta"')
    expect(source).toContain('const lastEffectiveCountByChapterId = ref({})')
    expect(source).toContain('const syncChapterWordBaseline = (chapterId, content = null) =>')
    expect(source).toContain('const primeTodayWordBaselines = () =>')
    expect(source).toContain('const delta = nextCount - previousCount')
    expect(source).toContain('preferenceStore.incrementTodayWordDelta(delta)')
    expect(source).not.toContain('preferenceStore.incrementTodayWordDelta(value)')
  })

  it('exposes a manual sync button that reuses flushCurrentDraftNow for chapter drafts only', () => {
    expect(source).toContain('<ManualSyncButton')
    expect(source).toContain('const handleManualSync = async () =>')
    expect(source).toContain('writeCachedDraft(chapterId, chapterDataStore.activeChapterContent)')
    expect(source).toContain('await flushCurrentDraftNow()')
  })
})

describe('WritingStudio focus mode', () => {
  let originalRequestAnimationFrame

  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
    vi.clearAllMocks()
    originalRequestAnimationFrame = globalThis.requestAnimationFrame
    globalThis.requestAnimationFrame = vi.fn((callback) => {
      callback()
      return 1
    })
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true
    })

    mockV1WorksGet.mockResolvedValue({
      id: 'work-1',
      title: '测试作品',
      author: '测试作者'
    })
    mockV1WorksUpdate.mockResolvedValue({
      id: 'work-1',
      title: '测试作品',
      author: '测试作者'
    })
    mockV1ChaptersList.mockResolvedValue([
      {
        id: 'chapter-1',
        title: '第一章',
        content: '第一章正文内容',
        order_index: 1,
        version: 3,
        updated_at: '2026-05-06T10:00:00.000Z'
      }
    ])
    mockV1ChaptersUpdate.mockResolvedValue({})
    mockV1ChaptersCreate.mockResolvedValue({})
    mockV1ChaptersDelete.mockResolvedValue({})
    mockV1ChaptersReorder.mockResolvedValue({ items: [] })
    mockV1ChaptersForceOverride.mockResolvedValue({})
    mockV1SessionsGet.mockResolvedValue({
      last_open_chapter_id: 'chapter-1',
      cursor_position: 2,
      scroll_top: 24,
      updated_at: '2026-05-06T10:00:00.000Z'
    })
    mockV1SessionsSave.mockResolvedValue({
      last_open_chapter_id: 'chapter-1',
      cursor_position: 2,
      scroll_top: 24,
      updated_at: '2026-05-06T10:00:00.000Z'
    })
  })

  afterEach(() => {
    globalThis.requestAnimationFrame = originalRequestAnimationFrame
  })

  it('keeps正文内容、光标和滚动位置在专注模式切换前后不变', async () => {
    const getViewportSpy = vi.fn()
    const restoreViewportSpy = vi.fn()
    const focusEditorSpy = vi.fn()
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          PureTextEditor: createPureTextEditorStub({
            getViewportSpy,
            restoreViewportSpy,
            focusEditorSpy
          }),
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    const chapterDataStore = useChapterDataStore()

    const textarea = wrapper.get('textarea')
    Object.defineProperty(textarea.element, 'scrollHeight', {
      configurable: true,
      value: 1200
    })
    Object.defineProperty(textarea.element, 'clientHeight', {
      configurable: true,
      value: 320
    })

    const originalNode = textarea.element
    originalNode.focus()
    originalNode.selectionStart = 5
    originalNode.selectionEnd = 5
    originalNode.scrollTop = 180

    expect(chapterDataStore.activeChapterContent).toBe('第一章正文内容')
    const focusToggle = wrapper.get('[data-test="focus-mode-toggle"]')
    await focusToggle.trigger('mousedown')
    await focusToggle.trigger('click')
    await flushStudio()

    expect(wrapper.find('.writing-studio').classes()).toContain('writing-studio--focus')
    expect(wrapper.find('.sidebar-column').attributes('style')).toContain('display: none;')
    expect(wrapper.find('.asset-rail-column').attributes('style')).toContain('display: none;')
    expect(wrapper.find('.status-bar-stub').exists()).toBe(true)
    expect(wrapper.get('textarea').element).toBe(originalNode)
    expect(chapterDataStore.activeChapterContent).toBe('第一章正文内容')
    const firstCapturedViewport = getViewportSpy.mock.calls[0]?.[0]
    expect(firstCapturedViewport).toBeTruthy()
    expect(firstCapturedViewport.scrollTop).toBe(180)
    expect(restoreViewportSpy).toHaveBeenCalledWith(firstCapturedViewport)
    expect(originalNode.selectionStart).toBe(firstCapturedViewport.cursorPosition)
    expect(originalNode.selectionEnd).toBe(firstCapturedViewport.cursorPosition)
    expect(originalNode.scrollTop).toBe(firstCapturedViewport.scrollTop)

    await focusToggle.trigger('mousedown')
    await focusToggle.trigger('click')
    await flushStudio()

    expect(wrapper.find('.writing-studio').classes()).not.toContain('writing-studio--focus')
    expect(wrapper.get('textarea').element).toBe(originalNode)
    expect(chapterDataStore.activeChapterContent).toBe('第一章正文内容')
    expect(restoreViewportSpy).toHaveBeenLastCalledWith(firstCapturedViewport)
    expect(originalNode.selectionStart).toBe(firstCapturedViewport.cursorPosition)
    expect(originalNode.selectionEnd).toBe(firstCapturedViewport.cursorPosition)
    expect(originalNode.scrollTop).toBe(firstCapturedViewport.scrollTop)
    expect(focusEditorSpy).toHaveBeenCalledTimes(3)
  })

  it('updates editor preferences locally without triggering chapter save requests', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    const preferenceStore = usePreferenceStore()

    await wrapper.get('[data-test="writing-preference-toggle"]').trigger('click')
    await flushStudio()

    expect(wrapper.find('[data-test="writing-preference-panel"]').exists()).toBe(true)

    await wrapper.get('[data-test="font-monospace"]').trigger('click')
    await wrapper.get('[data-test="font-size-select"]').setValue('24')
    await wrapper.get('[data-test="line-height-select"]').setValue('2')
    await wrapper.get('[data-test="theme-dark"]').trigger('click')
    await flushStudio()

    expect(preferenceStore.fontFamily).toBe('monospace')
    expect(preferenceStore.fontSize).toBe(24)
    expect(preferenceStore.lineHeight).toBe(2)
    expect(preferenceStore.theme).toBe('dark')
    expect(wrapper.get('.pure-text-editor').attributes('data-theme')).toBe('dark')
    expect(wrapper.get('textarea').attributes('style')).toContain('font-family: monospace;')
    expect(wrapper.get('textarea').attributes('style')).toContain('font-size: 24px;')
    expect(wrapper.get('textarea').attributes('style')).toContain('line-height: 2;')
    expect(mockV1ChaptersUpdate).not.toHaveBeenCalled()
  })

  it('shows the writing preference panel as a floating layer and closes on outside click or Escape', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    await wrapper.get('[data-test="writing-preference-toggle"]').trigger('click')
    await flushStudio()

    expect(wrapper.find('[data-test="writing-preference-floating-panel"]').exists()).toBe(true)

    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushStudio()
    expect(wrapper.find('[data-test="writing-preference-floating-panel"]').exists()).toBe(false)

    await wrapper.get('[data-test="writing-preference-toggle"]').trigger('click')
    await flushStudio()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushStudio()
    expect(wrapper.find('[data-test="writing-preference-floating-panel"]').exists()).toBe(false)
  })

  it('increments today word delta from正文输入 and ignores title edits', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    const preferenceStore = usePreferenceStore()

    expect(preferenceStore.todayWordDelta).toBe(0)

    await wrapper.get('.chapter-title-input-stub').setValue('新标题')
    await flushStudio()
    expect(preferenceStore.todayWordDelta).toBe(0)

    const textarea = wrapper.get('textarea')
    await textarea.setValue('第一章正文内容追加两字')
    await flushStudio()
    expect(preferenceStore.todayWordDelta).toBe(4)

    await textarea.setValue('')
    await flushStudio()
    expect(preferenceStore.todayWordDelta).toBe(0)
    expect(JSON.parse(window.localStorage.getItem('inktrace.preference.v1') || '{}').todayWordDelta).toBe(0)
  })

  it('flushes the current chapter immediately and clears local draft after manual sync success', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    mockV1ChaptersUpdate.mockResolvedValue({
      id: 'chapter-1',
      title: '第一章',
      content: '第一章正文内容立即同步',
      order_index: 1,
      version: 4,
      updated_at: '2026-05-06T12:00:00.000Z'
    })

    const textarea = wrapper.get('textarea')
    await textarea.setValue('第一章正文内容立即同步')
    await flushStudio()

    await wrapper.get('[data-test="manual-sync-button"]').trigger('click')
    await flushStudio()

    const { useSaveStateStore } = await import('@/stores/useSaveStateStore')
    const saveStateStore = useSaveStateStore()
    expect(mockV1ChaptersUpdate.mock.calls.length).toBeGreaterThan(0)
    expect(mockV1ChaptersUpdate).toHaveBeenLastCalledWith('chapter-1', expect.objectContaining({
      title: '第一章',
      content: '第一章正文内容立即同步',
      expected_version: 3
    }))
    expect(saveStateStore.pendingQueue).toEqual([])
  })

  it('keeps local draft when manual sync fails offline', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: false
    })

    const textarea = wrapper.get('textarea')
    await textarea.setValue('离线草稿保留')
    await flushStudio()

    await wrapper.get('[data-test="manual-sync-button"]').trigger('click')
    await flushStudio()

    expect(mockV1ChaptersUpdate).not.toHaveBeenCalled()
    const cacheIndex = JSON.parse(window.localStorage.getItem('inktrace:v1:cache:index') || '[]')
    const draftEntry = cacheIndex.find((entry) => String(entry?.key || '').includes('draft:work-1:chapter-1'))
    expect(draftEntry).toBeTruthy()
  })

  it('keeps local draft when manual sync fails with online error', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          AssetRail: AssetRailStub,
          AssetDrawer: AssetDrawerStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: buildAssetPanelStub('character-panel'),
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true
    })
    const error = new Error('save failed')
    error.response = { status: 500 }
    mockV1ChaptersUpdate.mockRejectedValueOnce(error)

    const textarea = wrapper.get('textarea')
    await textarea.setValue('在线失败保留草稿')
    await flushStudio()

    await wrapper.get('[data-test="manual-sync-button"]').trigger('click')
    await flushStudio()

    const { useSaveStateStore } = await import('@/stores/useSaveStateStore')
    const saveStateStore = useSaveStateStore()
    expect(mockV1ChaptersUpdate).toHaveBeenCalled()
    expect(saveStateStore.pendingQueue.length).toBeGreaterThan(0)
    expect(saveStateStore.readLocalDraft({ workId: 'work-1', chapterId: 'chapter-1' })).toMatchObject({
      content: '在线失败保留草稿'
    })
  })
})
