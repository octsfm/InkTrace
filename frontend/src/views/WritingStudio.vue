<template>
  <div class="writing-studio" :class="{ 'writing-studio--focus': isFocusMode }">
    <VersionConflictModal
      :model-value="conflictModalVisible"
      :description="conflictDescription"
      :local-content="conflictLocalContent"
      :server-content="conflictServerContent"
      @cancel="handleConflictCancel"
      @discard="handleConflictDiscard"
      @override="handleConflictOverride"
    />

    <header class="studio-header" :class="{ 'studio-header--focus': isFocusMode }">
      <div class="header-main">
        <div class="header-copy" :class="{ 'header-copy--muted': isFocusMode }">
          <button
            v-if="!workTitleEditing"
            type="button"
            class="work-title-button"
            @click="startWorkTitleEditing"
          >
            {{ workTitle }}
          </button>
          <input
            v-else
            ref="workTitleInputRef"
            v-model="workTitleDraft"
            class="work-title-input"
            type="text"
            maxlength="120"
            @keydown.enter.prevent="submitWorkTitleEditing"
            @keydown.esc.prevent="cancelWorkTitleEditing"
            @blur="submitWorkTitleEditing"
          />
          <p v-if="workAuthor">{{ workAuthor }}</p>
        </div>
        <div class="header-actions">
          <StatusBar
            :status="displaySaveStatus"
            :word-count="activeWordCount"
            :today-word-delta="preferenceStore.todayWordDelta"
            :session-ready="workspaceStore.hydrated"
            :offline="offlineBannerVisible"
            :offline-message="offlineBannerText"
            :last-synced-at="statusUpdatedAt"
            :status-detail="statusDetail"
            :retry-count="saveStateStore.retryCount"
            :next-retry-at="saveStateStore.nextRetryAt"
            :show-manual-retry="showManualRetry"
            @manual-retry="handleManualRetry"
          />
          <ManualSyncButton
            :disabled="!chapterDataStore.activeChapterId || conflictModalVisible"
            :saving="saveStateStore.saveStatus === 'saving'"
            @sync="handleManualSync"
          />
          <button
            v-show="!isFocusMode"
            type="button"
            class="preference-toggle"
            data-test="writing-preference-toggle"
            @click="togglePreferencePanel"
          >
            写作偏好
          </button>
          <FocusModeToggle
            :enabled="isFocusMode"
            @toggle="toggleFocusMode"
          />
          <el-button v-show="!isFocusMode" type="primary" @click="goBack">杩斿洖涔︽灦</el-button>
        </div>
      </div>
      <div v-show="preferencePanelVisible && !isFocusMode" class="header-panel-row">
        <WritingPreferencePanel
          :preferences="editorPreferences"
          @update-preferences="handlePreferenceUpdate"
          @close="preferencePanelVisible = false"
        />
      </div>
    </header>

    <section class="studio-shell" :class="{ 'studio-shell--focus': isFocusMode }">
      <aside v-show="!isFocusMode" class="sidebar-column">
        <div class="panel-card sidebar-card">
          <ChapterSidebar
            ref="sidebarRef"
            :chapters="chapterDataStore.chapters"
            :active-chapter-id="chapterDataStore.activeChapterId"
            :loading="chaptersLoading"
            :draft-chapter-ids="draftChapterIds"
            :conflict-chapter-id="conflictChapterId"
            @select="handleSelectChapter"
            @create="handleCreateChapter"
            @rename="handleRenameChapter"
            @delete="handleDeleteChapter"
            @reorder="handleReorderChapters"
            @jump-invalid="handleJumpInvalid"
          />
        </div>
      </aside>

      <main class="editor-column" :class="{ 'editor-column--focus': isFocusMode }">
        <div class="panel-card editor-card" :class="{ 'editor-card--focus': isFocusMode }">
          <div class="editor-shell">
            <ChapterTitleInput
              :model-value="chapterDataStore.activeChapterTitle"
              :order-index="activeChapterOrderIndex"
              :disabled="!chapterDataStore.activeChapterId"
              :placeholder="chapterTitlePlaceholder"
              @update:model-value="handleTitleInput"
            />
            <div class="editor-surface">
              <PureTextEditor
                ref="editorRef"
                :chapter-id="chapterDataStore.activeChapterId"
                :model-value="chapterDataStore.activeChapterContent"
                :placeholder="editorPlaceholder"
                :font-family="editorPreferences.fontFamily"
                :font-size="editorPreferences.fontSize"
                :line-height="editorPreferences.lineHeight"
                :theme="editorPreferences.theme"
                @update:model-value="handleDraftChange"
                @cursor-change="handleCursorChange"
                @scroll-change="handleScrollChange"
              />
            </div>
          </div>
        </div>
      </main>

      <aside v-show="!isFocusMode" class="asset-rail-column">
        <div class="panel-card asset-rail-card">
          <AssetRail
            :active-tab="activeAssetTab"
            @toggle="toggleAssetDrawer"
          />
        </div>
      </aside>

      <aside
        v-if="activeAssetTab"
        v-show="!isFocusMode"
        class="asset-drawer-column"
        :class="{ 'mobile-overlay-host': isMobileAssetDrawer }"
      >
        <AssetDrawer
          :visible="Boolean(activeAssetTab)"
          :active-tab="activeAssetTab"
          :dirty-tabs="assetDirtyTabs"
          :mobile="isMobileAssetDrawer"
          @close="closeAssetDrawer"
          @save-dirty="handleAssetSaveDirty"
          @discard-dirty="handleAssetDiscardDirty"
        >
          <template #default="{ activeTab }">
            <OutlinePanel
              v-if="activeTab === 'outline'"
              ref="outlinePanelRef"
              :work-id="workId"
              :active-chapter-id="chapterDataStore.activeChapterId"
              @focus-area="handleAssetFocusArea"
            />
            <TimelinePanel
              v-else-if="activeTab === 'timeline'"
              ref="timelinePanelRef"
              :work-id="workId"
              :chapters="chapterDataStore.chapters"
              @focus-area="handleAssetFocusArea"
            />
            <ForeshadowPanel
              v-else-if="activeTab === 'foreshadow'"
              ref="foreshadowPanelRef"
              :work-id="workId"
              :chapters="chapterDataStore.chapters"
              @focus-area="handleAssetFocusArea"
            />
            <CharacterPanel
              v-else-if="activeTab === 'character'"
              ref="characterPanelRef"
              :work-id="workId"
              @focus-area="handleAssetFocusArea"
            />
          </template>
        </AssetDrawer>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { v1ChaptersApi, v1WorksApi } from '@/api'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { useChapterDataStore } from '@/stores/useChapterDataStore'
import { useSaveStateStore } from '@/stores/useSaveStateStore'
import { usePreferenceStore } from '@/stores/preference'
import { useWritingAssetStore } from '@/stores/writingAsset'
import { countEffectiveCharacters } from '@/utils/textMetrics'
import AssetDrawer from '@/components/workspace/AssetDrawer.vue'
import AssetRail from '@/components/workspace/AssetRail.vue'
import CharacterPanel from '@/components/workspace/CharacterPanel.vue'
import ForeshadowPanel from '@/components/workspace/ForeshadowPanel.vue'
import FocusModeToggle from '@/components/workspace/FocusModeToggle.vue'
import ManualSyncButton from '@/components/workspace/ManualSyncButton.vue'
import OutlinePanel from '@/components/workspace/OutlinePanel.vue'
import TimelinePanel from '@/components/workspace/TimelinePanel.vue'
import WritingPreferencePanel from '@/components/workspace/WritingPreferencePanel.vue'
import ChapterSidebar from '@/components/workspace/ChapterSidebar.vue'
import ChapterTitleInput from '@/components/workspace/ChapterTitleInput.vue'
import PureTextEditor from '@/components/workspace/PureTextEditor.vue'
import StatusBar from '@/components/workspace/StatusBar.vue'
import VersionConflictModal from '@/components/workspace/VersionConflictModal.vue'

const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const chapterDataStore = useChapterDataStore()
const saveStateStore = useSaveStateStore()
const preferenceStore = usePreferenceStore()
const writingAssetStore = useWritingAssetStore()
const chaptersLoading = ref(false)
const pendingChapterId = ref('')
const editorRef = ref(null)
const sidebarRef = ref(null)
const workTitleInputRef = ref(null)
const outlinePanelRef = ref(null)
const timelinePanelRef = ref(null)
const foreshadowPanelRef = ref(null)
const characterPanelRef = ref(null)
const workTitle = ref('浣滃搧')
const workAuthor = ref('')
const workTitleEditing = ref(false)
const workTitleDraft = ref('')
let sessionSaveTimer = null
let draftSyncTimer = null
let retryTimer = null
let isDraftSyncing = false
const DRAFT_SYNC_DELAY_MS = 2500
const RETRY_DELAYS_MS = [1000, 2000, 4000]
const MOBILE_ASSET_BREAKPOINT = 760
const activeAssetTab = ref('')
const activeAssetFocusArea = ref('outline')
const isMobileAssetDrawer = ref(false)
const preferencePanelVisible = ref(false)
const lastEffectiveCountByChapterId = ref({})
const suppressDraftCaching = ref(false)

const workId = computed(() => String(route.params.id || ''))
const isFocusMode = computed(() => preferenceStore.focusMode)
const editorPreferences = computed(() => preferenceStore.editorPreferences)
const activeWordCount = computed(() => countEffectiveCharacters(chapterDataStore.activeChapterContent))
const assetDirtyTabs = computed(() => {
  const tabs = new Set()
  for (const key of writingAssetStore.dirtyAssetKeys) {
    if (key.startsWith('work_outline:') || key.startsWith('chapter_outline:')) {
      tabs.add('outline')
    } else if (key.startsWith('timeline:')) {
      tabs.add('timeline')
    } else if (key.startsWith('foreshadow:')) {
      tabs.add('foreshadow')
    } else if (key.startsWith('character:')) {
      tabs.add('character')
    }
  }
  return Array.from(tabs)
})
const statusUpdatedAt = computed(() => String(saveStateStore.lastSyncedAt || workspaceStore.sessionUpdatedAt || ''))
const conflictModalVisible = computed(() => saveStateStore.hasConflict)
const conflictPayload = computed(() => saveStateStore.conflictPayload)
const conflictChapterId = computed(() => String(saveStateStore.conflictPayload?.chapterId || ''))
const draftChapterIds = computed(() => {
  const ids = new Set([
    ...Object.keys(chapterDataStore.draftByChapterId || {}),
    ...Object.keys(chapterDataStore.draftTitleByChapterId || {}),
    ...saveStateStore.pendingQueue.map((item) => String(item?.chapterId || ''))
  ].filter(Boolean))
  return Array.from(ids)
})
const editorPlaceholder = computed(() => (
  chapterDataStore.activeChapterId ? '开始创作...' : '请先选择一个章节开始创作'
))
const chapterTitlePlaceholder = computed(() => (
  chapterDataStore.activeChapterId ? '输入章节标题' : '请先选择一个章节'
))
const resolveChapterOrderIndex = (chapter) => {
  const explicitOrder = Number(chapter?.order_index)
  if (Number.isFinite(explicitOrder) && explicitOrder > 0) {
    return explicitOrder
  }
  const index = chapterDataStore.chapters.findIndex((item) => item.id === chapter?.id)
  return index >= 0 ? index + 1 : 1
}
const buildChapterLabel = (chapter, title) => {
  const prefix = `第${resolveChapterOrderIndex(chapter)}章`
  const trimmedTitle = String(title || '').trim()
  return trimmedTitle ? `${prefix} ${trimmedTitle}` : prefix
}
const activeChapterOrderIndex = computed(() => resolveChapterOrderIndex(chapterDataStore.activeChapter))
const isOfflineMode = computed(() => saveStateStore.saveStatus === 'offline')
const displaySaveStatus = computed(() => {
  if (saveStateStore.saveStatus === 'saving') return 'saving'
  if (conflictModalVisible.value) return 'conflict'
  if (isOfflineMode.value) return 'offline'
  if (saveStateStore.saveStatus === 'error') return 'error'
  return 'synced'
})
const offlineBannerVisible = computed(() => isOfflineMode.value)
const offlineBannerText = computed(() => {
  if (saveStateStore.hasPendingDrafts) {
    return '离线模式：修改已写入本地缓存，恢复联网后会自动同步。'
  }
  return '离线模式：当前网络离线，编辑仍可继续。'
})
const statusDetail = computed(() => {
  if (conflictModalVisible.value) {
    return '检测到版本冲突，等待处理'
  }
  if (isOfflineMode.value && saveStateStore.hasPendingDrafts) {
    return `离线积压 ${saveStateStore.pendingQueue.length} 条草稿`
  }
  if (saveStateStore.saveStatus === 'saving' && saveStateStore.pendingQueue.length > 1) {
    return `正在同步 ${saveStateStore.pendingQueue.length} 条草稿`
  }
  if (saveStateStore.saveStatus === 'error' && saveStateStore.nextRetryAt) {
    return '后台重试中'
  }
  if (showManualRetry.value) {
    return '自动重试已停止'
  }
  return ''
})
const showManualRetry = computed(() => (
  saveStateStore.saveStatus === 'error' &&
  saveStateStore.hasPendingDrafts &&
  !saveStateStore.nextRetryAt &&
  !conflictModalVisible.value
))
const conflictDescription = computed(() => {
  const chapterTitle = String(
    conflictPayload.value?.chapterTitle ||
    chapterDataStore.activeChapterTitle ||
    buildChapterLabel(chapterDataStore.activeChapter, '') ||
    '当前章节'
  )
  return `${chapterTitle} 在云端已存在更新版本，请先决定是否覆盖。`
})
const conflictLocalContent = computed(() => String(conflictPayload.value?.content || ''))
const conflictServerContent = computed(() => String(
  conflictPayload.value?.server_content ||
  conflictPayload.value?.serverContent ||
  conflictPayload.value?.remote_content ||
  ''
))

const readCachedDraft = (chapterId) => saveStateStore.readLocalDraft({
  workId: workId.value,
  chapterId
})

const resolveChapterTitle = (chapterId) => {
  const id = String(chapterId || '')
  if (!id) return ''
  if (Object.prototype.hasOwnProperty.call(chapterDataStore.draftTitleByChapterId, id)) {
    return String(chapterDataStore.draftTitleByChapterId[id] || '')
  }
  return String(chapterDataStore.chapters.find((item) => item.id === id)?.title || '')
}

const resolveChapterContent = (chapterId) => {
  const id = String(chapterId || '')
  if (!id) return ''
  if (Object.prototype.hasOwnProperty.call(chapterDataStore.draftByChapterId, id)) {
    return String(chapterDataStore.draftByChapterId[id] || '')
  }
  return String(chapterDataStore.chapters.find((item) => item.id === id)?.content || '')
}

const writeCachedDraft = (chapterId, content) => {
  if (suppressDraftCaching.value) return null
  const chapter = chapterDataStore.chapters.find((item) => item.id === chapterId) || {}
  return saveStateStore.writeLocalDraft({
    workId: workId.value,
    chapterId,
    title: resolveChapterTitle(chapterId) || String(chapter.title || ''),
    content: typeof content === 'string' ? String(content) : resolveChapterContent(chapterId),
    version: Number(chapter.version || 0),
    cursorPosition: workspaceStore.cursorPosition,
    scrollTop: workspaceStore.scrollTop,
    timestamp: Date.now()
  })
}

const clearCachedDraft = (chapterId) => {
  saveStateStore.clearLocalDraft({
    workId: workId.value,
    chapterId
  })
}

const clearConflictState = () => {
  saveStateStore.clearConflict()
}

const scrollSidebarToChapter = async (chapterId) => {
  await nextTick()
  sidebarRef.value?.scrollToChapter?.(chapterId)
}

const focusEditor = async () => {
  await nextTick()
  editorRef.value?.focusEditor?.()
}

const captureActiveEditorViewport = () => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  const viewport = editorRef.value?.getViewport?.() || {
    cursorPosition: workspaceStore.cursorPosition,
    scrollTop: workspaceStore.scrollTop
  }
  if (chapterId) {
    workspaceStore.captureViewport({
      chapterId,
      cursorPosition: viewport.cursorPosition,
      scrollTop: viewport.scrollTop
    })
  }
  return viewport
}

const syncChapterWordBaseline = (chapterId, content = null) => {
  const id = String(chapterId || '')
  if (!id) return 0
  const resolvedContent = typeof content === 'string' ? content : resolveChapterContent(id)
  const nextCount = countEffectiveCharacters(resolvedContent)
  lastEffectiveCountByChapterId.value = {
    ...lastEffectiveCountByChapterId.value,
    [id]: nextCount
  }
  return nextCount
}

const primeTodayWordBaselines = () => {
  const nextMap = {}
  chapterDataStore.chapters.forEach((chapter) => {
    const chapterId = String(chapter.id || '')
    if (!chapterId) return
    nextMap[chapterId] = countEffectiveCharacters(resolveChapterContent(chapterId))
  })
  lastEffectiveCountByChapterId.value = nextMap
}

const blockSidebarMutation = () => {
  if (saveStateStore.saveStatus === 'saving') {
    ElMessage.warning('姝ｅ湪鍚屾鏁版嵁锛岃绋嶅€?..')
    return true
  }
  return false
}

const clearRetryTimer = () => {
  if (!retryTimer) return
  clearTimeout(retryTimer)
  retryTimer = null
}

const loadCachedDrafts = (chapters) => {
  const cachedDrafts = []
  chapters.forEach((chapter) => {
    const cached = readCachedDraft(chapter.id)
    if (!cached || typeof cached !== 'object') return
    if (typeof cached.content === 'string') {
      chapterDataStore.updateChapterDraft(chapter.id, cached.content)
      chapterDataStore.updateChapterTitleDraft(chapter.id, String(cached.title || chapter.title || ''))
      cachedDrafts.push({
        chapterId: chapter.id,
        title: String(cached.title || chapter.title || ''),
        content: cached.content,
        timestamp: cached.timestamp
      })
    }
    workspaceStore.setViewport(chapter.id, {
      cursorPosition: cached.cursorPosition,
      scrollTop: cached.scrollTop
    })
  })
  saveStateStore.replaceQueue([
    ...saveStateStore.pendingQueue,
    ...cachedDrafts
  ])
}

const loadChapters = async () => {
  chaptersLoading.value = true
  try {
    return await v1ChaptersApi.list(workId.value)
  } catch (error) {
    console.error('加载章节列表失败:', error)
    ElMessage.error('章节列表加载失败，请稍后重试。')
    return []
  } finally {
    chaptersLoading.value = false
  }
}

const refreshChapters = async () => {
  const chapters = await loadChapters()
  chapterDataStore.setChapters(chapters)
  return chapters
}

const restoreViewportForChapter = async (chapterId) => {
  const id = String(chapterId || '')
  if (!id) return
  await nextTick()
  editorRef.value?.restoreViewport(workspaceStore.getViewport(id))
}

const scheduleSessionSave = () => {
  if (!workId.value || !workspaceStore.lastOpenChapterId) return
  if (sessionSaveTimer) {
    clearTimeout(sessionSaveTimer)
  }
  sessionSaveTimer = setTimeout(async () => {
    await persistSessionNow()
  }, 800)
}

const persistSessionNow = async () => {
  if (!workId.value || !workspaceStore.lastOpenChapterId) return
  if (sessionSaveTimer) {
    clearTimeout(sessionSaveTimer)
    sessionSaveTimer = null
  }
  try {
    await workspaceStore.saveSessionPosition()
  } catch (error) {
    console.error('淇濆瓨缂栬緫浼氳瘽澶辫触:', error)
  }
}

const scheduleDraftSync = () => {
  if (conflictModalVisible.value) return
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer)
  }
  draftSyncTimer = setTimeout(() => {
    draftSyncTimer = null
    flushDraftQueue()
  }, DRAFT_SYNC_DELAY_MS)
}

const scheduleRetry = (attemptIndex) => {
  const delay = RETRY_DELAYS_MS[attemptIndex]
  if (!delay) {
    saveStateStore.setRetrySchedule({ retryCount: attemptIndex, nextRetryAt: '' })
    return
  }
  clearRetryTimer()
  const scheduledAt = new Date(Date.now() + delay).toISOString()
  saveStateStore.setRetrySchedule({
    retryCount: attemptIndex + 1,
    nextRetryAt: scheduledAt
  })
  retryTimer = setTimeout(() => {
    retryTimer = null
    saveStateStore.setRetrySchedule({
      retryCount: attemptIndex + 1,
      nextRetryAt: ''
    })
    flushDraftQueue({
      retryAttempt: attemptIndex + 1
    })
  }, delay)
}

const collectOfflineDrafts = () => {
  const cachedDrafts = saveStateStore.collectLocalDrafts(workId.value)

  const merged = new Map()
  for (const draft of [...saveStateStore.pendingQueue, ...cachedDrafts]) {
    const chapterId = String(draft?.chapterId || '')
    if (!chapterId) continue
    const normalized = {
      ...draft,
      chapterId,
      timestamp: Number(draft?.timestamp) || Date.now()
    }
    const existing = merged.get(chapterId)
    if (!existing || normalized.timestamp >= existing.timestamp) {
      merged.set(chapterId, normalized)
    }
  }
  return Array.from(merged.values()).sort((left, right) => Number(left.timestamp || 0) - Number(right.timestamp || 0))
}

const flushDraftQueue = async ({ retryAttempt = 0, manual = false } = {}) => {
  if (conflictModalVisible.value || isDraftSyncing || !saveStateStore.pendingQueue.length) return
  if (manual) {
    clearRetryTimer()
    saveStateStore.setRetrySchedule({
      retryCount: saveStateStore.retryCount,
      nextRetryAt: ''
    })
  }
  isDraftSyncing = true
  saveStateStore.markSaving()
  let lastUpdatedAt = ''
  let currentDraft = null
  try {
    const replayResult = await saveStateStore.replayOfflineDrafts({
      replay: async (draft) => {
        currentDraft = draft
        const chapter = chapterDataStore.chapters.find((item) => item.id === draft.chapterId)
        if (!chapter) {
          clearCachedDraft(draft.chapterId)
          chapterDataStore.clearChapterDraft(draft.chapterId)
          currentDraft = null
          return
        }
        const savedChapter = await v1ChaptersApi.update(draft.chapterId, {
          title: String(draft.title || ''),
          content: draft.content,
          expected_version: chapter.version
        })
        lastUpdatedAt = String(savedChapter?.updated_at || lastUpdatedAt)
        chapterDataStore.upsertChapter(savedChapter)
        const latestDraftContent = chapterDataStore.draftByChapterId[draft.chapterId]
        const latestDraftTitle = chapterDataStore.draftTitleByChapterId[draft.chapterId]
        const contentMatches = latestDraftContent === undefined || String(latestDraftContent) === String(draft.content || '')
        const titleMatches = latestDraftTitle === undefined || String(latestDraftTitle) === String(draft.title || '')
        if (contentMatches && titleMatches) {
          chapterDataStore.clearChapterDraft(draft.chapterId)
          chapterDataStore.clearChapterTitleDraft(draft.chapterId)
          clearCachedDraft(draft.chapterId)
        }
        currentDraft = null
      }
    })
    if (replayResult?.successCount >= 0) {
      saveStateStore.markSynced(lastUpdatedAt || new Date().toISOString())
    }
  } catch (error) {
    if (error?.response?.status === 409 && currentDraft) {
      clearRetryTimer()
      const chapter = chapterDataStore.chapters.find((item) => item.id === currentDraft.chapterId)
      saveStateStore.markConflict({
        ...currentDraft,
        title: String(currentDraft.title || ''),
        chapterTitle: String(currentDraft.title || chapter?.title || '')
      }, String(error.userMessage || '检测到版本冲突，请先决定是否覆盖。'))
      saveStateStore.setRetrySchedule({ retryCount: retryAttempt, nextRetryAt: '' })
    } else {
      if (currentDraft) {
        saveStateStore.upsertDraft(currentDraft)
      }
      const message = String(error?.userMessage || error?.message || '保存失败')
      if (!navigator.onLine || !error?.response) {
        clearRetryTimer()
        saveStateStore.markOffline()
      } else {
        saveStateStore.markError(message)
        scheduleRetry(retryAttempt)
      }
    }
  } finally {
    isDraftSyncing = false
    if (
      !conflictModalVisible.value &&
      saveStateStore.pendingQueue.length &&
      !saveStateStore.nextRetryAt &&
      saveStateStore.saveStatus !== 'error'
    ) {
      scheduleDraftSync()
    }
  }
}

const replayOfflineDrafts = async () => {
  if (!navigator.onLine || conflictModalVisible.value) return
  const offlineDrafts = collectOfflineDrafts()
  if (!offlineDrafts.length) {
    if (saveStateStore.saveStatus === 'offline') {
      saveStateStore.markSynced(saveStateStore.lastSyncedAt || new Date().toISOString())
    }
    return
  }
  saveStateStore.replaceQueue(offlineDrafts)
  await flushDraftQueue()
}

const flushCurrentDraftNow = async () => {
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer)
    draftSyncTimer = null
  }
  if (!saveStateStore.pendingQueue.length) return
  if (!navigator.onLine || isOfflineMode.value) {
    saveStateStore.markOffline()
    return
  }
  await flushDraftQueue({
    retryAttempt: saveStateStore.retryCount,
    manual: true
  })
}

const handleBrowserOffline = () => {
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer)
    draftSyncTimer = null
  }
  clearRetryTimer()
  saveStateStore.markOffline()
}

const handleBrowserOnline = async () => {
  if (conflictModalVisible.value) return
  await replayOfflineDrafts()
}

const handleCachePruned = () => {
  ElMessage.warning('本地缓存空间不足，已自动清理较旧的暂存内容。')
}

const syncAssetDrawerViewport = () => {
  isMobileAssetDrawer.value = typeof window !== 'undefined' && window.innerWidth <= MOBILE_ASSET_BREAKPOINT
}

const saveFocusedAssetDraft = async () => {
  if (!activeAssetTab.value) return false
  if (activeAssetTab.value === 'outline') {
    await outlinePanelRef.value?.saveFocusedDraft?.(activeAssetFocusArea.value)
    return true
  }
  if (activeAssetTab.value === 'timeline') {
    const mode = activeAssetFocusArea.value === 'timeline_reorder' ? 'reorder' : 'event'
    await timelinePanelRef.value?.saveFocusedDraft?.(mode)
    return true
  }
  if (activeAssetTab.value === 'foreshadow') {
    await foreshadowPanelRef.value?.saveFocusedDraft?.()
    return true
  }
  if (activeAssetTab.value === 'character') {
    await characterPanelRef.value?.saveFocusedDraft?.()
    return true
  }
  return false
}

const handleEditorSaveShortcut = async (event) => {
  const key = String(event?.key || '').toLowerCase()
  if (key !== 's' || (!event?.ctrlKey && !event?.metaKey)) return
  const activeElement = document.activeElement
  const insideEditor = Boolean(activeElement?.closest?.('.editor-shell'))
  const insideAssetPanel = Boolean(activeElement?.closest?.('.asset-drawer-body'))
  if (!insideEditor && !insideAssetPanel) return
  event.preventDefault()
  if (insideEditor) {
    await flushCurrentDraftNow()
    await persistSessionNow()
    return
  }
  await saveFocusedAssetDraft()
}

const activateChapter = async (chapterId) => {
  const nextChapterId = String(chapterId || '')
  if (!nextChapterId) return
  pendingChapterId.value = ''
  chapterDataStore.setActiveChapter(nextChapterId)
  syncChapterWordBaseline(nextChapterId)
  workspaceStore.setLastOpenChapter(nextChapterId)
  await scrollSidebarToChapter(nextChapterId)
  await restoreViewportForChapter(nextChapterId)
  scheduleSessionSave()
}

onMounted(async () => {
  preferenceStore.hydrate()
  syncAssetDrawerViewport()
  saveStateStore.setSaveStatus('synced')
  saveStateStore.clearConflict()
  saveStateStore.clearRetrySchedule()
  window.addEventListener('offline', handleBrowserOffline)
  window.addEventListener('online', handleBrowserOnline)
  window.addEventListener('inktrace-cache-pruned', handleCachePruned)
  window.addEventListener('keydown', handleEditorSaveShortcut)
  window.addEventListener('resize', syncAssetDrawerViewport)
  let workspacePayload = null
  let chapters = []
  try {
    const [workspaceResult, loadedChapters] = await Promise.all([
      workspaceStore.initializeWorkspace(workId.value),
      loadChapters()
    ])
    workspacePayload = workspaceResult
    chapters = loadedChapters
    workTitle.value = String(workspaceResult?.work?.title || '未命名作品')
    workAuthor.value = String(workspaceResult?.work?.author || '').trim()
  } catch (error) {
    console.error('初始化写作工作台失败:', error)
    workTitle.value = '未命名作品'
    workAuthor.value = ''
  }
  chapterDataStore.setChapters(chapters)
  loadCachedDrafts(chapters)
  primeTodayWordBaselines()
  const session = workspacePayload?.session || workspaceStore.session || null
  const sessionChapterId = String(session?.last_open_chapter_id || session?.chapter_id || '')
  const matchedSessionChapter = chapters.find((chapter) => chapter.id === sessionChapterId)
  const initialChapterId = matchedSessionChapter?.id || chapters[0]?.id || ''
  if (initialChapterId) {
    await activateChapter(initialChapterId)
    await focusEditor()
  }
  if (!navigator.onLine) {
    saveStateStore.markOffline()
  } else {
    await replayOfflineDrafts()
  }
})

onBeforeUnmount(() => {
  if (sessionSaveTimer) {
    clearTimeout(sessionSaveTimer)
    sessionSaveTimer = null
  }
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer)
    draftSyncTimer = null
  }
  clearRetryTimer()
  window.removeEventListener('offline', handleBrowserOffline)
  window.removeEventListener('online', handleBrowserOnline)
  window.removeEventListener('inktrace-cache-pruned', handleCachePruned)
  window.removeEventListener('keydown', handleEditorSaveShortcut)
  window.removeEventListener('resize', syncAssetDrawerViewport)
})

watch(
  () => saveStateStore.saveStatus,
  async (status) => {
    if (status === 'saving' || !pendingChapterId.value) return
    await activateChapter(pendingChapterId.value)
  }
)

const goBack = () => {
  router.push('/works')
}

const toggleFocusMode = async () => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  const preservedViewport = captureActiveEditorViewport()
  if (!isFocusMode.value) {
    preferencePanelVisible.value = false
  }
  preferenceStore.toggleFocusMode()
  await nextTick()
  editorRef.value?.focusEditor?.()
  if (chapterId) {
    editorRef.value?.restoreViewport(preservedViewport)
  }
}

const togglePreferencePanel = () => {
  preferencePanelVisible.value = !preferencePanelVisible.value
}

const handlePreferenceUpdate = (patch = {}) => {
  preferenceStore.updateWritingPreferences(patch)
}

const toggleAssetDrawer = (tabKey) => {
  const nextKey = String(tabKey || '')
  activeAssetFocusArea.value = nextKey || activeAssetFocusArea.value
  activeAssetTab.value = activeAssetTab.value === nextKey ? '' : nextKey
}

const closeAssetDrawer = () => {
  activeAssetTab.value = ''
}

const handleAssetFocusArea = (area) => {
  activeAssetFocusArea.value = String(area || activeAssetTab.value || 'outline')
}

const handleAssetSaveDirty = (tabKey) => {
  const nextKey = String(tabKey || '')
  if (nextKey === 'outline') {
    return outlinePanelRef.value?.saveFocusedDraft?.(activeAssetFocusArea.value)
  }
  if (nextKey === 'timeline') {
    return timelinePanelRef.value?.saveFocusedDraft?.()
  }
  if (nextKey === 'foreshadow') {
    return foreshadowPanelRef.value?.saveFocusedDraft?.()
  }
  if (nextKey === 'character') {
    return characterPanelRef.value?.saveFocusedDraft?.()
  }
  return undefined
}

const handleAssetDiscardDirty = (tabKey) => {
  const nextKey = String(tabKey || '')
  if (nextKey === 'outline') {
    return outlinePanelRef.value?.discardFocusedDraft?.(activeAssetFocusArea.value)
  }
  if (nextKey === 'timeline') {
    return timelinePanelRef.value?.discardFocusedDraft?.()
  }
  if (nextKey === 'foreshadow') {
    return foreshadowPanelRef.value?.discardFocusedDraft?.()
  }
  if (nextKey === 'character') {
    return characterPanelRef.value?.discardFocusedDraft?.()
  }
  return undefined
}

const startWorkTitleEditing = async () => {
  workTitleDraft.value = String(workTitle.value || '').trim()
  workTitleEditing.value = true
  await nextTick()
  workTitleInputRef.value?.focus?.()
  workTitleInputRef.value?.select?.()
}

const cancelWorkTitleEditing = async () => {
  workTitleEditing.value = false
  workTitleDraft.value = String(workTitle.value || '')
  await focusEditor()
}

const submitWorkTitleEditing = async () => {
  if (!workTitleEditing.value) return
  const nextTitle = String(workTitleDraft.value || '').trim()
  const currentTitle = String(workTitle.value || '').trim()
  if (!nextTitle || nextTitle === currentTitle) {
    await cancelWorkTitleEditing()
    return
  }
  try {
    const updated = await v1WorksApi.update(workId.value, { title: nextTitle })
    workTitle.value = String(updated?.title || nextTitle)
    workAuthor.value = String(updated?.author || workAuthor.value || '').trim()
    workTitleEditing.value = false
    ElMessage.success('作品标题已更新。')
  } catch (error) {
    console.error('更新作品标题失败:', error)
    workTitleEditing.value = false
    workTitleDraft.value = currentTitle
    ElMessage.error('作品标题更新失败，请稍后重试。')
  } finally {
    await focusEditor()
  }
}

const handleSelectChapter = async (chapterId) => {
  const nextChapterId = String(chapterId || '')
  if (!nextChapterId || nextChapterId === chapterDataStore.activeChapterId) return
  const currentChapterId = String(chapterDataStore.activeChapterId || '')
  if (currentChapterId) {
    writeCachedDraft(currentChapterId, chapterDataStore.activeChapterContent)
  }
  await activateChapter(nextChapterId)
  await focusEditor()
}

const handleJumpInvalid = () => {
  ElMessage.warning('请输入有效章节编号。')
}

const handleDraftChange = (content) => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId) return
  const previousCount = Object.prototype.hasOwnProperty.call(lastEffectiveCountByChapterId.value, chapterId)
    ? Number(lastEffectiveCountByChapterId.value[chapterId] || 0)
    : countEffectiveCharacters(chapterDataStore.activeChapterContent)
  const nextCount = countEffectiveCharacters(content)
  const delta = nextCount - previousCount
  syncChapterWordBaseline(chapterId, content)
  preferenceStore.incrementTodayWordDelta(delta)
  if (saveStateStore.nextRetryAt || saveStateStore.retryCount) {
    clearRetryTimer()
    saveStateStore.clearRetrySchedule()
  }
  chapterDataStore.updateChapterDraft(chapterId, content)
  workspaceStore.setLastOpenChapter(chapterId)
  writeCachedDraft(chapterId, content)
  if (!conflictModalVisible.value) {
    if (!navigator.onLine || isOfflineMode.value) {
      saveStateStore.markOffline()
    } else {
      saveStateStore.markSaving()
      scheduleDraftSync()
    }
  }
  scheduleSessionSave()
}

const handleTitleInput = (value) => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId) return
  if (saveStateStore.nextRetryAt || saveStateStore.retryCount) {
    clearRetryTimer()
    saveStateStore.clearRetrySchedule()
  }
  const nextTitle = String(value || '').trim()
  chapterDataStore.updateChapterTitleDraft(chapterId, nextTitle)
  workspaceStore.setLastOpenChapter(chapterId)
  writeCachedDraft(chapterId)
  if (!conflictModalVisible.value) {
    if (!navigator.onLine || isOfflineMode.value) {
      saveStateStore.markOffline()
    } else {
      saveStateStore.markSaving()
      scheduleDraftSync()
    }
  }
  scheduleSessionSave()
}

const handleCursorChange = ({ cursorPosition = 0 } = {}) => {
  workspaceStore.captureViewport({
    chapterId: chapterDataStore.activeChapterId,
    cursorPosition,
    scrollTop: workspaceStore.scrollTop
  })
  if (
    chapterDataStore.activeChapterId &&
    (
      chapterDataStore.draftByChapterId[chapterDataStore.activeChapterId] !== undefined ||
      chapterDataStore.draftTitleByChapterId[chapterDataStore.activeChapterId] !== undefined
    )
  ) {
    writeCachedDraft(chapterDataStore.activeChapterId, chapterDataStore.activeChapterContent)
  }
  scheduleSessionSave()
}

const handleScrollChange = ({ scrollTop = 0 } = {}) => {
  workspaceStore.captureViewport({
    chapterId: chapterDataStore.activeChapterId,
    cursorPosition: workspaceStore.cursorPosition,
    scrollTop
  })
  if (
    chapterDataStore.activeChapterId &&
    (
      chapterDataStore.draftByChapterId[chapterDataStore.activeChapterId] !== undefined ||
      chapterDataStore.draftTitleByChapterId[chapterDataStore.activeChapterId] !== undefined
    )
  ) {
    writeCachedDraft(chapterDataStore.activeChapterId, chapterDataStore.activeChapterContent)
  }
  scheduleSessionSave()
}

const handleCreateChapter = async () => {
  if (!workId.value || blockSidebarMutation()) return
  try {
    const lastChapterId = String(chapterDataStore.chapters.at(-1)?.id || '')
    const createdChapter = await v1ChaptersApi.create(workId.value, {
      title: '',
      after_chapter_id: lastChapterId
    })
    const chapters = await refreshChapters()
    const nextChapterId = String(createdChapter?.id || chapters.at(-1)?.id || '')
    if (nextChapterId) {
      await activateChapter(nextChapterId)
      await focusEditor()
    }
    ElMessage.success('已新建章节。')
  } catch (error) {
    console.error('新建章节失败:', error)
  }
}

const handleRenameChapter = async ({ chapterId = '', title = '' } = {}) => {
  const id = String(chapterId || '')
  const nextTitle = String(title || '').trim()
  if (!id || !nextTitle || blockSidebarMutation()) return
  const chapter = chapterDataStore.chapters.find((item) => item.id === id)
  if (!chapter || nextTitle === String(chapter.title || '').trim()) return
  try {
    const savedChapter = await v1ChaptersApi.update(id, {
      title: nextTitle,
      expected_version: Number(chapter.version || 0)
    })
    chapterDataStore.upsertChapter(savedChapter)
    chapterDataStore.clearChapterTitleDraft(id)
    ElMessage.success('章节标题已更新。')
  } catch (error) {
    console.error('重命名章节失败:', error)
  }
}

const handleDeleteChapter = async (chapterId) => {
  const id = String(chapterId || '')
  if (!id || blockSidebarMutation()) return
  if (!window.confirm('确认删除该章节吗？')) return
  const wasActive = id === chapterDataStore.activeChapterId
  const nextActiveIdFallback = wasActive
    ? ''
    : String(chapterDataStore.activeChapterId || '')
  try {
    const result = await v1ChaptersApi.delete(id)
    pendingChapterId.value = pendingChapterId.value === id ? '' : pendingChapterId.value
    saveStateStore.removeDraft(id)
    chapterDataStore.clearChapterDraft(id)
    chapterDataStore.clearChapterTitleDraft(id)
    clearCachedDraft(id)
    const chapters = await refreshChapters()
    const nextChapterId = wasActive
      ? String(result?.next_chapter_id || chapters[0]?.id || '')
      : nextActiveIdFallback
    if (nextChapterId) {
      await activateChapter(nextChapterId)
    } else {
      chapterDataStore.setActiveChapter('')
      workspaceStore.setLastOpenChapter('')
    }
    ElMessage.success('章节已删除。')
  } catch (error) {
    console.error('删除章节失败:', error)
  }
}

const handleReorderChapters = async (chapterIds) => {
  const orderedIds = Array.isArray(chapterIds) ? chapterIds.map((item) => String(item || '')).filter(Boolean) : []
  if (!workId.value || orderedIds.length !== chapterDataStore.chapters.length || blockSidebarMutation()) return
  try {
    const response = await v1ChaptersApi.reorder(workId.value, orderedIds)
    chapterDataStore.setChapters(response?.items || [])
    ElMessage.success('章节顺序已更新。')
  } catch (error) {
    console.error('调序章节失败:', error)
  }
}

const handleConflictDiscard = async () => {
  const chapterId = String(conflictPayload.value?.chapterId || '')
  if (!chapterId) {
    clearConflictState()
    return
  }
  const chapters = await refreshChapters()
  const latestChapter = chapters.find((item) => item.id === chapterId)
  chapterDataStore.clearChapterDraft(chapterId)
  chapterDataStore.clearChapterTitleDraft(chapterId)
  saveStateStore.removeDraft(chapterId)
  saveStateStore.clearRetrySchedule()
  clearCachedDraft(chapterId)
  workspaceStore.setViewport(chapterId, {
    cursorPosition: 0,
    scrollTop: 0
  })
  clearConflictState()
  if (latestChapter) {
    await activateChapter(chapterId)
    saveStateStore.markSynced(String(latestChapter.updated_at || new Date().toISOString()))
  } else {
    saveStateStore.markSynced()
  }
  ElMessage.success('已放弃本地修改，并重新加载云端内容。')
  if (saveStateStore.pendingQueue.length) {
    scheduleDraftSync()
  }
}

const handleConflictCancel = () => {
  // Keep the conflict payload and local draft untouched.
}

const handleConflictOverride = async () => {
  const chapterId = String(conflictPayload.value?.chapterId || '')
  if (!chapterId) {
    clearConflictState()
    return
  }
  const latestContent = Object.prototype.hasOwnProperty.call(chapterDataStore.draftByChapterId, chapterId)
    ? String(chapterDataStore.draftByChapterId[chapterId] || '')
    : String(conflictPayload.value?.content || '')
  const latestTitle = Object.prototype.hasOwnProperty.call(chapterDataStore.draftTitleByChapterId, chapterId)
    ? String(chapterDataStore.draftTitleByChapterId[chapterId] || '')
    : String(conflictPayload.value?.title || '')
  const chapter = chapterDataStore.chapters.find((item) => item.id === chapterId)
  saveStateStore.markSaving()
  try {
    const savedChapter = await v1ChaptersApi.forceOverride(chapterId, {
      title: latestTitle,
      content: latestContent,
      expected_version: Number(chapter?.version || 0)
    })
    chapterDataStore.upsertChapter(savedChapter)
    chapterDataStore.clearChapterDraft(chapterId)
    chapterDataStore.clearChapterTitleDraft(chapterId)
    saveStateStore.removeDraft(chapterId)
    saveStateStore.clearRetrySchedule()
    clearCachedDraft(chapterId)
    clearConflictState()
    await activateChapter(chapterId)
    saveStateStore.markSynced(String(savedChapter?.updated_at || new Date().toISOString()))
    ElMessage.success('已使用本地内容覆盖云端版本。')
    if (saveStateStore.pendingQueue.length) {
      scheduleDraftSync()
    }
  } catch (error) {
    const message = String(error?.userMessage || error?.message || '强制覆盖失败')
    saveStateStore.markError(message)
  }
}

const handleManualRetry = async () => {
  if (!saveStateStore.pendingQueue.length) return
  await flushDraftQueue({
    retryAttempt: saveStateStore.retryCount,
    manual: true
  })
}

const handleManualSync = async () => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId || conflictModalVisible.value) return
  writeCachedDraft(chapterId, chapterDataStore.activeChapterContent)
  suppressDraftCaching.value = true
  try {
    await flushCurrentDraftNow()
    if (saveStateStore.saveStatus === 'synced' && !saveStateStore.hasPendingDrafts) {
      await nextTick()
      chapterDataStore.clearChapterDraft(chapterId)
      chapterDataStore.clearChapterTitleDraft(chapterId)
      clearCachedDraft(chapterId)
    }
  } finally {
    suppressDraftCaching.value = false
  }
}
</script>

<style scoped>
.writing-studio {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px 20px 24px;
  gap: 16px;
  background: #f8fafc;
}

.writing-studio--focus {
  background: #f3f4f6;
}

.studio-header {
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #ffffff;
  padding: 20px 24px;
}

.studio-header--focus {
  padding: 16px 20px;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.header-copy h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.work-title-button {
  display: block;
  max-width: min(520px, 52vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: none;
  background: transparent;
  padding: 0;
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  cursor: pointer;
  text-align: left;
}

.work-title-input {
  width: min(520px, 100%);
  border: 1px solid #d1d5db;
  border-radius: 14px;
  background: #ffffff;
  padding: 10px 14px;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  outline: none;
}

.work-title-input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.header-copy p {
  margin-top: 8px;
  color: #4b5563;
}

.header-copy--muted p {
  color: #9ca3af;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-panel-row {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.preference-toggle {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #ffffff;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
}

.preference-toggle:hover {
  border-color: #93c5fd;
  color: #1d4ed8;
}

.studio-shell {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 72px;
  gap: 16px;
}

.studio-shell--focus {
  grid-template-columns: minmax(0, 1fr);
}

.sidebar-column,
.editor-column,
.asset-rail-column,
.asset-drawer-column {
  min-height: 0;
}

.editor-column--focus {
  max-width: 960px;
  width: min(100%, 960px);
  margin: 0 auto;
}

.panel-card {
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #ffffff;
}

.panel-card {
  padding: 20px;
}

.sidebar-card {
  padding: 18px;
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-title-row h2 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.panel-title-row span {
  font-size: 12px;
  color: #6b7280;
}

.panel-description {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: #6b7280;
}

.editor-card {
  display: flex;
  flex-direction: column;
}

.editor-card--focus {
  border-color: #dbeafe;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
}

.editor-shell {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: start;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.editor-surface {
  flex: 1;
  min-height: 0;
  border-radius: 20px;
  background: #ffffff;
  padding: 0;
  display: flex;
}

.asset-rail-card {
  padding: 10px;
}

.asset-drawer-column {
  width: 360px;
}

@media (max-width: 1120px) {
  .studio-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .writing-studio {
    padding: 16px;
  }

  .header-main,
  .header-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .asset-drawer-column.mobile-overlay-host {
    width: 0;
    min-width: 0;
    min-height: 0;
  }
}
</style>

