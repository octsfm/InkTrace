import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { webcrypto } from 'node:crypto'
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
const mockAIGetSettings = vi.fn()
const mockAITestProvider = vi.fn()
const mockAIStartInitialization = vi.fn()
const mockAIGetJob = vi.fn()
const mockAIGetLatestInitialization = vi.fn()
const mockAIBuildContextPack = vi.fn()
const mockAIGetContextPackReadiness = vi.fn()
const mockAIStartContinuation = vi.fn()
const mockAIListCandidateDrafts = vi.fn()
const mockAIGetCandidateDraft = vi.fn()
const mockAIAcceptCandidateDraft = vi.fn()
const mockAIRejectCandidateDraft = vi.fn()
const mockAIApplyCandidateDraft = vi.fn()
const mockAIRunQuickTrial = vi.fn()
const mockAIReviewCandidateDraft = vi.fn()
const mockAIGetAIReview = vi.fn()
const mockAICreateSelectionRewrite = vi.fn()
const mockAIGetSelectionRewrite = vi.fn()
const mockAIApplySelectionRewrite = vi.fn()
const mockAIRejectSelectionRewrite = vi.fn()
const mockAISuggestMentions = vi.fn()
const mockAIGetChapterMentions = vi.fn()
const mockAIReplaceChapterMentions = vi.fn()
const elMessage = {
  warning: vi.fn(),
  error: vi.fn(),
  success: vi.fn(),
  info: vi.fn()
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

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => ['enable_selection_rewrite', 'enable_mentions'].includes(flagName)
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
  },
  aiApi: {
    getAISettings: mockAIGetSettings,
    testProvider: mockAITestProvider,
    startInitialization: mockAIStartInitialization,
    getAIJob: mockAIGetJob,
    getLatestInitialization: mockAIGetLatestInitialization,
    buildContextPack: mockAIBuildContextPack,
    getContextPackReadiness: mockAIGetContextPackReadiness,
    startContinuation: mockAIStartContinuation,
    listCandidateDrafts: mockAIListCandidateDrafts,
    getCandidateDraft: mockAIGetCandidateDraft,
    acceptCandidateDraft: mockAIAcceptCandidateDraft,
    rejectCandidateDraft: mockAIRejectCandidateDraft,
    applyCandidateDraft: mockAIApplyCandidateDraft,
    runQuickTrial: mockAIRunQuickTrial,
    reviewCandidateDraft: mockAIReviewCandidateDraft,
    getAIReview: mockAIGetAIReview,
    createSelectionRewrite: mockAICreateSelectionRewrite,
    getSelectionRewrite: mockAIGetSelectionRewrite,
    applySelectionRewrite: mockAIApplySelectionRewrite,
    rejectSelectionRewrite: mockAIRejectSelectionRewrite,
    suggestMentions: mockAISuggestMentions,
    getChapterMentions: mockAIGetChapterMentions,
    replaceChapterMentions: mockAIReplaceChapterMentions
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

const RightWorkspacePanelStub = defineComponent({
  name: 'RightWorkspacePanelStub',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  setup(props, { slots }) {
    return () => h('div', { class: 'right-workspace-panel__body' }, slots.default?.({ activeTab: props.modelValue }) || [])
  }
})

const ReviewTabStub = defineComponent({
  name: 'ReviewTabStub',
  setup() {
    return () => h('div', { class: 'review-tab-stub' })
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
  focusEditorSpy = vi.fn(),
  insertPlainTextAtSelectionSpy = vi.fn()
} = {}) => defineComponent({
  name: 'PureTextEditorStub',
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue', 'cursor-change', 'selection-change', 'scroll-change'],
  setup(props, { emit, expose }) {
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

    const insertPlainTextAtSelection = (text) => {
      const target = textareaRef.value
      if (!target) return undefined
      const source = String(props.modelValue || '')
      const start = Number(target.selectionStart || 0)
      const end = Number(target.selectionEnd || 0)
      const nextValue = `${source.slice(0, start)}${text}${source.slice(end)}`
      insertPlainTextAtSelectionSpy(text, { start, end, nextValue })
      target.value = nextValue
      const nextCursor = start + String(text || '').length
      target.selectionStart = nextCursor
      target.selectionEnd = nextCursor
      emit('update:modelValue', nextValue)
      emit('cursor-change', {
        cursorPosition: nextCursor
      })
      return {
        text,
        start,
        end: nextCursor
      }
    }

    expose({
      getViewport,
      restoreViewport,
      focusEditor,
      insertPlainTextAtSelection
    })

    return () => h('textarea', {
      ref: textareaRef,
      class: 'pure-text-editor-stub',
      value: props.modelValue,
      onInput: (event) => {
        emit('update:modelValue', event.target.value)
        emit('cursor-change', {
          cursorPosition: Number(event.target.selectionStart || event.target.value.length || 0)
        })
      },
      onClick: (event) => {
        emit('cursor-change', {
          cursorPosition: Number(event.target.selectionStart || 0)
        })
      }
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
    expect(source).toContain('class="right-workspace-column"')
    expect(source).toContain('<ChapterSidebar')
    expect(source).toContain('<ChapterTitleInput')
    expect(source).toContain('<PureTextEditor')
    expect(source).toContain('<RightWorkspacePanel')
    expect(source).toContain('<ReviewTab')
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

  it('keeps the right workspace panel as a single tab host controlled by activeWorkspaceTab', () => {
    expect(source).toContain('const activeWorkspaceTab = ref')
    expect(source).toContain(':model-value="activeWorkspaceTab"')
    expect(source).toContain('@update:model-value="handleWorkspaceTabChange"')
    expect(source).toContain('class="right-workspace-column"')
    expect(source).toContain('handleWorkspaceTabChange')
  })

  it('uses mobile overlay wiring for the right workspace without creating a separate page', () => {
    expect(source).toContain('const MOBILE_ASSET_BREAKPOINT = 760')
    expect(source).toContain('const isMobileWorkspacePanel = ref(false)')
    expect(source).toContain('const syncWorkspaceViewport = () =>')
    expect(source).toContain("window.addEventListener('resize', syncWorkspaceViewport)")
    expect(source).toContain("window.removeEventListener('resize', syncWorkspaceViewport)")
    expect(source).toContain(":mobile=\"isMobileWorkspacePanel\"")
    expect(source).not.toContain("router.push('/assets'")
  })

  it('mounts outline timeline and foreshadow asset panels inside the right workspace panel', () => {
    expect(source).toContain('<OutlinePanel')
    expect(source).toContain('<TimelinePanel')
    expect(source).toContain('<ForeshadowPanel')
    expect(source).toContain('<CharacterPanel')
    expect(source).toContain('<AIPanel')
    expect(source).toContain("v-else-if=\"activeTab === 'review'\"")
    expect(source).not.toContain('outline_file')
    expect(source).not.toContain('导入大纲')
  })

  it('moves ai panel into the right workspace tabs instead of keeping it below the editor', () => {
    expect(source).toContain("activeTab === 'ai'")
    expect(source).toContain("mode=\"ai\"")
    expect(source).toContain(':chapter-id="chapterDataStore.activeChapterId"')
    expect(source).toContain('@open-review-tab="handleAIPanelOpenReviewTab"')
    expect(source).not.toContain('<AIPanel\n              v-show="!isFocusMode"')
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
    expect(source).toContain('activeElement?.closest?.(\'.right-workspace-panel__body\')')
    expect(source).toContain('event.preventDefault()')
    expect(source).toContain('await flushCurrentDraftNow()')
  })

  it('routes Ctrl/Cmd+S inside the right workspace only to the focused asset panel', () => {
    expect(source).toContain('const saveFocusedAssetDraft = async')
    expect(source).toContain("if (activeWorkspaceTab.value === 'outline')")
    expect(source).toContain('outlinePanelRef.value?.saveFocusedDraft?.(activeAssetFocusArea.value)')
    expect(source).toContain("if (activeWorkspaceTab.value === 'timeline')")
    expect(source).toContain("activeAssetFocusArea.value === 'timeline_reorder' ? 'reorder' : 'event'")
    expect(source).toContain('timelinePanelRef.value?.saveFocusedDraft?.(mode)')
    expect(source).toContain("if (activeWorkspaceTab.value === 'foreshadow')")
    expect(source).toContain('foreshadowPanelRef.value?.saveFocusedDraft?.()')
    expect(source).toContain("if (activeWorkspaceTab.value === 'character')")
    expect(source).toContain('characterPanelRef.value?.saveFocusedDraft?.()')
    expect(source).not.toContain("activeElement?.closest?.('.right-workspace-tab-rail')")
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
    expect(source).toContain("return '当前离线:内容已暂存本地,网络恢复后自动同步。'")
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
    expect(source).toContain("ElMessage.warning('本地缓存空间不足,已自动清理较旧的暂存内容。')")
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
    expect(source).toContain(':theme="preferenceStore.appTheme"')
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

  it('wires selection rewrite toolbar modal and editor selection handlers into the studio shell', () => {
    expect(source).toContain('<SelectionRewriteToolbar')
    expect(source).toContain(':floating-style="selectionRewriteToolbarStyle"')
    expect(source).toContain(':placement="selectionRewriteToolbarPlacement"')
    expect(source).toContain('<SelectionRewriteDiffModal')
    expect(source).toContain(':waiting-user-action="selectionRewriteStore.status === \'pending\'"')
    expect(source).toContain(':conflicted="selectionRewriteStore.status === \'conflicted\'"')
    expect(source).toContain(':conflict-message="selectionRewriteStore.actionError"')
    expect(source).toContain(':busy="selectionRewriteStore.loading"')
    expect(source).toContain(":polling=\"selectionRewriteStore.status === 'generating'\"")
    expect(source).toContain(':applying="selectionRewriteStore.applying"')
    expect(source).toContain('@selection-change="handleSelectionChange"')
    expect(source).toContain('@mode-select="handleSelectionRewriteMode"')
    expect(source).toContain('@clear-history="handleSelectionRewriteClearHistory"')
    expect(source).toContain('@accept="handleSelectionRewriteAccept"')
    expect(source).toContain('@reject="handleSelectionRewriteReject"')
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
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: webcrypto
    })
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true
    })

    mockAIGetSettings.mockResolvedValue({
      data: {
        provider_configs: [],
        model_role_mappings: {}
      }
    })
    mockAITestProvider.mockResolvedValue({ data: { test_status: 'ok', message: 'ok' } })
    mockAIStartInitialization.mockResolvedValue({ data: { initialization_id: 'init_1', job_id: 'job_1' } })
    mockAIGetJob.mockResolvedValue({ data: { job_id: 'job_1', status: 'completed', steps: [] } })
    mockAIGetLatestInitialization.mockResolvedValue({
      data: {
        status: 'completed',
        analyzed_chapter_count: 0,
        empty_chapter_count: 0,
        failed_chapter_count: 0
      }
    })
    mockAIBuildContextPack.mockResolvedValue({ data: { context_pack_id: 'cp_1', status: 'ready' } })
    mockAIGetContextPackReadiness.mockResolvedValue({
      data: {
        status: 'ready',
        blocked_reason: '',
        degraded_reason: '',
        warnings: []
      }
    })
    mockAIStartContinuation.mockResolvedValue({
      data: {
        job_id: 'job_2',
        candidate_draft_id: 'cd_1',
        status: 'completed_with_candidate'
      }
    })
    mockAIListCandidateDrafts.mockResolvedValue({ data: { items: [] } })
    mockAIGetCandidateDraft.mockResolvedValue({ data: { candidate_draft_id: 'cd_1', content: '候选稿内容' } })
    mockAIAcceptCandidateDraft.mockResolvedValue({ data: { status: 'accepted' } })
    mockAIRejectCandidateDraft.mockResolvedValue({ data: { status: 'rejected' } })
    mockAIApplyCandidateDraft.mockResolvedValue({ data: { status: 'applied' } })
    mockAIRunQuickTrial.mockResolvedValue({ data: { status: 'succeeded', output_text: '试跑输出', validation_status: 'passed' } })
    mockAIReviewCandidateDraft.mockResolvedValue({ data: { review_id: 'rv_1', status: 'succeeded', summary: '审阅完成' } })
    mockAIGetAIReview.mockResolvedValue({ data: { review_id: 'rv_1', summary: '审阅完成', issues: [], suggestions: [], risk_level: 'low' } })
    mockAISuggestMentions.mockResolvedValue({ data: { suggestions: [] } })
    mockAIGetChapterMentions.mockResolvedValue({ data: { mentions: [] } })
    mockAIReplaceChapterMentions.mockResolvedValue({ data: { mentions: [] } })

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
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    expect(wrapper.find('.right-workspace-column').attributes('style')).toContain('display: none;')
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
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    await flushStudio()

    expect(preferenceStore.fontFamily).toBe('monospace')
    expect(preferenceStore.fontSize).toBe(24)
    expect(preferenceStore.lineHeight).toBe(2)
    expect(preferenceStore.editorTheme).toBe(preferenceStore.appTheme)
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
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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

  it('shows selection rewrite toolbar for valid selection and hides it after draft content changes', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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

    const editor = wrapper.findComponent({ name: 'PureTextEditor' })
    editor.vm.$emit('selection-change', {
      text: '第一章正文内容',
      start: 0,
      end: 8
    })
    await flushStudio()

    expect(wrapper.find('[data-test="selection-rewrite-toolbar"]').exists()).toBe(true)
    const textarea = wrapper.get('textarea')
    await textarea.setValue('第一章正文内容新增一句')
    await flushStudio()

    expect(wrapper.find('[data-test="selection-rewrite-toolbar"]').exists()).toBe(false)
  })

  it('positions selection rewrite toolbar from editor selection anchor payload', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const editor = wrapper.getComponent({ name: 'PureTextEditor' })
    editor.vm.$emit('selection-change', {
      text: '第一章正文内容',
      start: 0,
      end: 8,
      anchorX: 188,
      anchorY: 84,
      anchorHeight: 24,
      containerWidth: 640
    })
    await flushStudio()

    const toolbar = wrapper.get('[data-test="selection-rewrite-toolbar"]')
    expect(toolbar.attributes('style')).toContain('left: 188px;')
    expect(toolbar.attributes('style')).toContain('top: 108px;')
    expect(toolbar.classes()).toContain('selection-rewrite-toolbar--below')
  })

  it('delegates selection rewrite result polling to the store instead of manually reloading in the page', () => {
    expect(source).toContain('const handleSelectionRewriteMode = async (mode) => {')
    expect(source).toContain('await selectionRewriteStore.createRewrite(mode)')
    expect(source).not.toContain('await selectionRewriteStore.loadRewriteResult(created.rewrite_id)')
  })

  it('shows async terminal selection rewrite errors once per unique rewrite status', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const { useSelectionRewriteStore } = await import('@/stores/useSelectionRewriteStore')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const selectionRewriteStore = useSelectionRewriteStore()

    selectionRewriteStore.activeRewriteId = 'srw_001'
    selectionRewriteStore.status = 'failed'
    selectionRewriteStore.actionError = '选区改写生成失败,请稍后重试。'
    await flushStudio()

    expect(elMessage.error).toHaveBeenCalledTimes(1)
    const failedToastPayload = elMessage.error.mock.calls[0][0]
    expect(failedToastPayload.duration).toBe(5000)
    expect(failedToastPayload.message.children[0].children).toBe('选区改写生成失败,请稍后重试。')

    selectionRewriteStore.actionError = ''
    await flushStudio()
    selectionRewriteStore.actionError = '选区改写生成失败,请稍后重试。'
    await flushStudio()

    expect(elMessage.error).toHaveBeenCalledTimes(1)

    selectionRewriteStore.status = 'conflicted'
    selectionRewriteStore.actionError = '原文已变化,请重新选择。'
    selectionRewriteStore.modalVisible = true
    selectionRewriteStore.selectionText = '月光落在窗台上'
    await flushStudio()

    expect(elMessage.error).toHaveBeenCalledTimes(1)
    expect(elMessage.warning).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('原文已变化,请重新选择。')

    wrapper.unmount()
  })

  it('supports reselect action for conflicted selection rewrite terminal state', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const { useSelectionRewriteStore } = await import('@/stores/useSelectionRewriteStore')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const selectionRewriteStore = useSelectionRewriteStore()
    selectionRewriteStore.activeRewriteId = 'srw_001'
    selectionRewriteStore.requestId = 'job_001'
    selectionRewriteStore.status = 'conflicted'
    selectionRewriteStore.actionError = '原文已变化,请重新选择。'
    selectionRewriteStore.selectionText = '月光落在窗台上'
    selectionRewriteStore.selectionStart = 4
    selectionRewriteStore.selectionEnd = 12
    selectionRewriteStore.modalVisible = true
    selectionRewriteStore.candidate = {
      rewrite_id: 'srw_001',
      status: 'conflicted'
    }

    await flushStudio()

    await wrapper.get('[data-test="selection-rewrite-conflict-reselect"]').trigger('click')
    await flushStudio()

    expect(selectionRewriteStore.activeRewriteId).toBe('')
    expect(selectionRewriteStore.requestId).toBe('')
    expect(selectionRewriteStore.status).toBe('')
    expect(selectionRewriteStore.selectionText).toBe('')
    expect(selectionRewriteStore.modalVisible).toBe(false)

    wrapper.unmount()
  })

  it('shows retry action for failed selection rewrite terminal state', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const { useSelectionRewriteStore } = await import('@/stores/useSelectionRewriteStore')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const selectionRewriteStore = useSelectionRewriteStore()
    selectionRewriteStore.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3,
      draftRevision: 12
    })
    selectionRewriteStore.setSelection({
      text: '月光落在窗台上',
      start: 4,
      end: 12
    })
    selectionRewriteStore.lastRequestedMode = 'polish'
    selectionRewriteStore.activeRewriteId = 'srw_001'
    selectionRewriteStore.status = 'failed'
    selectionRewriteStore.actionError = '选区改写生成失败,请稍后重试。'
    await flushStudio()

    const errorPayload = elMessage.error.mock.calls[0][0]
    const retryButtonVNode = errorPayload.message.children[1]
    mockAICreateSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_002',
        status: 'generating',
        request_id: 'job_002'
      }
    })

    await retryButtonVNode.props.onClick()
    await flushStudio()

    expect(mockAICreateSelectionRewrite).toHaveBeenCalled()

    wrapper.unmount()
  })

  it('shows undo toast after applying selection rewrite and reverts draft when undo is clicked', async () => {
    mockAIApplySelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'applied',
        patch: {
          range: [6, 13],
          replacement: '月光静静落在旧窗台上'
        }
      }
    })

    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const { useSelectionRewriteStore } = await import('@/stores/useSelectionRewriteStore')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const chapterStore = useChapterDataStore()
    const selectionRewriteStore = useSelectionRewriteStore()

    chapterStore.updateChapterDraft('chapter-1', '这是旧文本,月光落在窗台上,风吹进来。')
    selectionRewriteStore.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3,
      draftRevision: 12
    })
    selectionRewriteStore.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      source_start_pos: 6,
      source_end_pos: 13,
      rewritten_text: '月光静静落在旧窗台上'
    }
    selectionRewriteStore.activeRewriteId = 'srw_001'
    selectionRewriteStore.editedText = '月光静静落在旧窗台上'
    selectionRewriteStore.modalVisible = true

    await wrapper.vm.handleSelectionRewriteAccept({ finalText: '月光静静落在旧窗台上' })
    await flushStudio()

    expect(elMessage.success).toHaveBeenCalledTimes(1)
    const successPayload = elMessage.success.mock.calls[0][0]
    expect(successPayload.duration).toBe(5000)
    const undoButtonVNode = successPayload.message.children[1]
    await undoButtonVNode.props.onClick()
    await flushStudio()

    expect(chapterStore.activeChapterContent).toBe('这是旧文本,月光落在窗台上,风吹进来。')

    wrapper.unmount()
  })

  it('shows manual retry error when local selection rewrite patch apply fails', async () => {
    mockAIApplySelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'applied',
        patch: {
          range: [6, 13],
          replacement: '月光静静落在旧窗台上'
        }
      }
    })

    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const { useSelectionRewriteStore } = await import('@/stores/useSelectionRewriteStore')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const chapterStore = useChapterDataStore()
    const selectionRewriteStore = useSelectionRewriteStore()
    const originalDraft = chapterStore.activeChapterContent

    selectionRewriteStore.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3,
      draftRevision: 12
    })
    selectionRewriteStore.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending',
      source_start_pos: 6,
      source_end_pos: 13,
      source_text: '月光落在窗台上',
      rewritten_text: '月光静静落在旧窗台上'
    }
    selectionRewriteStore.activeRewriteId = 'srw_001'
    selectionRewriteStore.editedText = '月光静静落在旧窗台上'
    selectionRewriteStore.modalVisible = true

    await wrapper.vm.handleSelectionRewriteAccept({ finalText: '月光静静落在旧窗台上' })
    await flushStudio()

    expect(elMessage.error).toHaveBeenCalledWith('改写结果已确认，但本地草稿应用失败，请手动重试。')
    expect(chapterStore.activeChapterContent).toBe(originalDraft)
    expect(selectionRewriteStore.modalVisible).toBe(true)

    wrapper.unmount()
  })

  it('shows rejected toast after selection rewrite reject succeeds', async () => {
    mockAIRejectSelectionRewrite.mockResolvedValue({
      data: {
        rewrite_id: 'srw_001',
        status: 'rejected'
      }
    })

    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const { useSelectionRewriteStore } = await import('@/stores/useSelectionRewriteStore')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
    const selectionRewriteStore = useSelectionRewriteStore()
    selectionRewriteStore.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3,
      draftRevision: 12
    })
    selectionRewriteStore.selectionText = '月光落在窗台上'
    selectionRewriteStore.selectionStart = 4
    selectionRewriteStore.selectionEnd = 12
    selectionRewriteStore.activeRewriteId = 'srw_001'
    selectionRewriteStore.modalVisible = true
    selectionRewriteStore.candidate = {
      rewrite_id: 'srw_001',
      status: 'pending'
    }

    await wrapper.vm.handleSelectionRewriteReject()
    await flushStudio()

    expect(elMessage.info).toHaveBeenCalledWith({
      duration: 2000,
      message: '已拒绝'
    })
    expect(selectionRewriteStore.selectionText).toBe('')

    wrapper.unmount()
  })

  it('loads chapter mentions on activation, shows popup after @ input, and saves mentions after chapter save succeeds', async () => {
    mockAIGetChapterMentions.mockResolvedValue({
      data: {
        mentions: [{
          mention_id: 'm_existing',
          chapter_id: 'chapter-1',
          work_id: 'work-1',
          entity_type: 'character',
          entity_id: 'char_existing',
          entity_name_snapshot: '李四',
          start_pos: 0,
          end_pos: 3,
          source: 'user_input',
          status: 'active',
          is_active: true,
          ai_suggestion_id: '',
          validation_detail: '',
          created_at: '2026-07-03T12:00:00Z',
          updated_at: '2026-07-03T12:00:00Z'
        }]
      }
    })
    mockAISuggestMentions.mockResolvedValue({
      data: {
        suggestions: [{
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name: '张三',
          match_type: 'prefix',
          summary_preview: '主角'
        }]
      }
    })
    mockAIReplaceChapterMentions.mockResolvedValue({
      data: {
        mentions: [{
          mention_id: 'm_new',
          chapter_id: 'chapter-1',
          work_id: 'work-1',
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name_snapshot: '张三',
          start_pos: 4,
          end_pos: 7,
          source: 'user_input',
          status: 'active',
          is_active: true,
          ai_suggestion_id: '',
          validation_detail: '',
          created_at: '2026-07-03T12:00:00Z',
          updated_at: '2026-07-03T12:00:00Z'
        }]
      }
    })
    mockV1ChaptersUpdate.mockResolvedValue({
      id: 'chapter-1',
      title: '第一章',
      content: '他说@张三',
      order_index: 1,
      version: 4,
      updated_at: '2026-05-06T12:00:00.000Z'
    })

    const insertPlainTextAtSelectionSpy = vi.fn()
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          PureTextEditor: createPureTextEditorStub({
            insertPlainTextAtSelectionSpy
          }),
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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

    expect(mockAIGetChapterMentions).toHaveBeenCalledWith('chapter-1')

    const textarea = wrapper.get('textarea')
    await textarea.setValue('他说@张')
    textarea.element.selectionStart = 4
    textarea.element.selectionEnd = 4
    await textarea.trigger('click')
    await flushStudio()

    expect(mockAISuggestMentions).toHaveBeenCalledWith({
      work_id: 'work-1',
      q: '张',
      types: 'character,event,foreshadow',
      limit: 10
    })
    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(true)

    await wrapper.get('[data-test="mention-popup-option-char_001"]').trigger('click')
    await flushStudio()

    expect(insertPlainTextAtSelectionSpy).toHaveBeenCalledWith('@张三', expect.any(Object))
    await wrapper.get('[data-test="manual-sync-button"]').trigger('click')
    await flushStudio()

    expect(mockV1ChaptersUpdate).toHaveBeenLastCalledWith('chapter-1', expect.objectContaining({
      title: '第一章',
      content: '他说@张三',
      expected_version: 4
    }))
    expect(mockAIReplaceChapterMentions).toHaveBeenLastCalledWith('chapter-1', {
      chapter_revision: 4,
      mentions: [expect.objectContaining({
        entity_type: 'character',
        entity_id: 'char_001',
        entity_name_snapshot: '张三',
        start_pos: 2,
        end_pos: 5,
        source: 'user_input',
        ai_suggestion_id: ''
      })]
    })
  })

  it('closes mention popup when Escape is pressed', async () => {
    mockAISuggestMentions.mockResolvedValue({
      data: {
        suggestions: [{
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name: '张三',
          match_type: 'prefix',
          summary_preview: '主角'
        }]
      }
    })

    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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

    const textarea = wrapper.get('textarea')
    await textarea.setValue('他说@张')
    textarea.element.selectionStart = 4
    textarea.element.selectionEnd = 4
    await textarea.trigger('click')
    await flushStudio()

    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(true)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushStudio()

    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(false)
  })

  it('supports ArrowDown and Enter to pick the active mention suggestion', async () => {
    mockAISuggestMentions.mockResolvedValue({
      data: {
        suggestions: [{
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name: '张三',
          match_type: 'prefix',
          summary_preview: '主角'
        }, {
          entity_type: 'event',
          entity_id: 'event_001',
          entity_name: '雨夜决战',
          match_type: 'prefix',
          summary_preview: '关键事件'
        }]
      }
    })

    const insertPlainTextAtSelectionSpy = vi.fn()
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          PureTextEditor: createPureTextEditorStub({
            insertPlainTextAtSelectionSpy
          }),
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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

    const textarea = wrapper.get('textarea')
    await textarea.setValue('他说@张')
    textarea.element.selectionStart = 4
    textarea.element.selectionEnd = 4
    await textarea.trigger('click')
    await flushStudio()

    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(true)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    await flushStudio()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    await flushStudio()

    expect(insertPlainTextAtSelectionSpy).toHaveBeenCalledWith('@雨夜决战', expect.any(Object))
    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(false)
  })

  it('routes empty mention results to character creation entry', async () => {
    mockAISuggestMentions.mockResolvedValue({
      data: {
        suggestions: []
      }
    })

    const startCreateSpy = vi.fn()
    const CharacterPanelCreateStub = defineComponent({
      name: 'CharacterPanelStub',
      setup(_, { expose }) {
        expose({
          saveFocusedDraft: vi.fn(async () => {}),
          discardFocusedDraft: vi.fn(),
          startCreate: startCreateSpy
        })
        return () => h('div', { class: 'character-panel-stub' })
      }
    })

    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
          OutlinePanel: buildAssetPanelStub('outline-panel'),
          TimelinePanel: buildAssetPanelStub('timeline-panel'),
          ForeshadowPanel: buildAssetPanelStub('foreshadow-panel'),
          CharacterPanel: CharacterPanelCreateStub,
          StatusBar: StatusBarStub,
          VersionConflictModal: VersionConflictModalStub,
          'el-button': {
            template: '<button class="el-button-stub"><slot /></button>'
          }
        }
      }
    })

    await flushStudio()

    const textarea = wrapper.get('textarea')
    await textarea.setValue('他说@赵云')
    textarea.element.selectionStart = 5
    textarea.element.selectionEnd = 5
    await textarea.trigger('click')
    await flushStudio()

    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="mention-popup-create-character"]').exists()).toBe(true)

    await wrapper.get('[data-test="mention-popup-create-character"]').trigger('click')
    await flushStudio()

    expect(startCreateSpy).toHaveBeenCalled()
    expect(wrapper.find('.character-panel-stub').exists()).toBe(true)
  })

  it('flushes the current chapter immediately and clears local draft after manual sync success', async () => {
    const { default: WritingStudio } = await import('../WritingStudio.vue')
    const wrapper = mount(WritingStudio, {
      global: {
        stubs: {
          ChapterSidebar: ChapterSidebarStub,
          ChapterTitleInput: ChapterTitleInputStub,
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
          RightWorkspacePanel: RightWorkspacePanelStub,
          ReviewTab: ReviewTabStub,
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
