<template>
  <div class="writing-studio">
    <VersionConflictModal
      :model-value="conflictModalVisible"
      :description="conflictDescription"
      @discard="handleConflictDiscard"
      @override="handleConflictOverride"
    />

    <header class="studio-header">
      <div class="header-main">
        <div class="header-copy">
          <h1>{{ workTitle }}</h1>
          <p v-if="workAuthor">{{ workAuthor }}</p>
        </div>
        <div class="header-actions">
          <StatusBar
            :status="displaySaveStatus"
            :word-count="activeWordCount"
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
          <el-button type="primary" @click="goBack">返回书架</el-button>
        </div>
      </div>
    </header>

    <section class="studio-shell">
      <aside class="sidebar-column">
        <div class="panel-card sidebar-card">
          <ChapterSidebar
            ref="sidebarRef"
            :chapters="chapterDataStore.chapters"
            :active-chapter-id="chapterDataStore.activeChapterId"
            :loading="chaptersLoading"
            @select="handleSelectChapter"
            @create="handleCreateChapter"
            @rename="handleRenameChapter"
            @delete="handleDeleteChapter"
            @reorder="handleReorderChapters"
          />
        </div>
      </aside>

      <main class="editor-column">
        <div class="panel-card editor-card">
          <div class="editor-shell">
            <input
              :value="activeChapterInputValue"
              class="chapter-title-input"
              type="text"
              :disabled="!chapterDataStore.activeChapterId"
              :placeholder="chapterTitlePlaceholder"
              maxlength="120"
              @input="handleTitleInput"
            />
            <div class="editor-surface">
              <PureTextEditor
                ref="editorRef"
                :chapter-id="chapterDataStore.activeChapterId"
                :model-value="chapterDataStore.activeChapterContent"
                :placeholder="editorPlaceholder"
                @update:model-value="handleDraftChange"
                @cursor-change="handleCursorChange"
                @scroll-change="handleScrollChange"
              />
            </div>
          </div>
        </div>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { v1ChaptersApi, v1SessionsApi, v1WorksApi } from '@/api'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { useChapterDataStore } from '@/stores/useChapterDataStore'
import { useSaveStateStore } from '@/stores/useSaveStateStore'
import { localCache } from '@/utils/localCache'
import { countEffectiveCharacters } from '@/utils/textMetrics'
import ChapterSidebar from '@/components/workspace/ChapterSidebar.vue'
import PureTextEditor from '@/components/workspace/PureTextEditor.vue'
import StatusBar from '@/components/workspace/StatusBar.vue'
import VersionConflictModal from '@/components/workspace/VersionConflictModal.vue'

const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const chapterDataStore = useChapterDataStore()
const saveStateStore = useSaveStateStore()
const chaptersLoading = ref(false)
const pendingChapterId = ref('')
const editorRef = ref(null)
const sidebarRef = ref(null)
const workTitle = ref('作品')
const workAuthor = ref('')
let sessionSaveTimer = null
let draftSyncTimer = null
let retryTimer = null
let isDraftSyncing = false
const DRAFT_SYNC_DELAY_MS = 2500
const RETRY_DELAYS_MS = [1000, 2000, 4000]
const conflictModalVisible = ref(false)
const conflictPayload = ref(null)

const workId = computed(() => String(route.params.id || ''))
const activeWordCount = computed(() => countEffectiveCharacters(chapterDataStore.activeChapterContent))
const statusUpdatedAt = computed(() => String(saveStateStore.lastSyncedAt || workspaceStore.sessionUpdatedAt || ''))
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
const activeChapterInputValue = computed(() => {
  const chapter = chapterDataStore.activeChapter
  if (!chapter) return ''
  return buildChapterLabel(chapter, chapterDataStore.activeChapterTitle)
})
const isOfflineMode = computed(() => saveStateStore.saveStatus === 'offline')
const displaySaveStatus = computed(() => {
  if (saveStateStore.saveStatus === 'saving') return 'saving'
  if (conflictModalVisible.value) return 'error'
  if (saveStateStore.saveStatus === 'error') return 'error'
  if (isOfflineMode.value) {
    return saveStateStore.hasPendingDrafts ? 'error' : 'synced'
  }
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

const buildDraftCacheKey = (chapterId) => `draft:${workId.value}:${String(chapterId || '')}`

const readCachedDraft = (chapterId) => localCache.get(buildDraftCacheKey(chapterId), null)

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

const parseEditableTitle = (rawTitle) => {
  const text = String(rawTitle || '').trim()
  return text.replace(/^第\d+章\s*/, '').trim()
}

const writeCachedDraft = (chapterId, content) => {
  const chapter = chapterDataStore.chapters.find((item) => item.id === chapterId) || {}
  localCache.set(buildDraftCacheKey(chapterId), {
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
  localCache.remove(buildDraftCacheKey(chapterId))
}

const clearConflictState = () => {
  conflictModalVisible.value = false
  conflictPayload.value = null
}

const scrollSidebarToChapter = async (chapterId) => {
  await nextTick()
  sidebarRef.value?.scrollToChapter?.(chapterId)
}

const focusEditor = async () => {
  await nextTick()
  editorRef.value?.focusEditor?.()
}

const blockSidebarMutation = () => {
  if (saveStateStore.saveStatus === 'saving') {
    ElMessage.warning('正在同步数据，请稍候...')
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

const loadWork = async () => {
  if (!workId.value) return null
  try {
    const work = await v1WorksApi.get(workId.value)
    workTitle.value = String(work?.title || '未命名作品')
    workAuthor.value = String(work?.author || '').trim()
    return work
  } catch (error) {
    console.error('加载作品信息失败:', error)
    workTitle.value = '未命名作品'
    workAuthor.value = ''
    return null
  }
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

const loadSession = async () => {
  try {
    const session = await v1SessionsApi.get(workId.value)
    workspaceStore.hydrateSession(session)
    return session
  } catch (error) {
    console.error('加载编辑会话失败:', error)
    workspaceStore.resetSession()
    return null
  }
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
    sessionSaveTimer = null
    try {
      const session = await v1SessionsApi.save(workId.value, workspaceStore.toSessionPayload())
      workspaceStore.markPersisted(session?.updated_at)
    } catch (error) {
      console.error('保存编辑会话失败:', error)
    }
  }, 800)
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
  const prefix = `draft:${workId.value}:`
  const cachedDrafts = localCache.keys()
    .filter((key) => key.startsWith(prefix))
    .map((key) => {
      const cached = localCache.get(key, null)
      if (!cached || typeof cached !== 'object') return null
      const chapterId = String(cached.chapterId || key.slice(prefix.length))
      return {
        chapterId,
        title: String(cached.title || resolveChapterTitle(chapterId) || ''),
        content: String(cached.content || ''),
        timestamp: cached.timestamp,
        cursorPosition: cached.cursorPosition,
        scrollTop: cached.scrollTop
      }
    })
    .filter(Boolean)

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
      conflictPayload.value = {
        ...currentDraft,
        title: String(currentDraft.title || ''),
        chapterTitle: String(currentDraft.title || chapter?.title || '')
      }
      conflictModalVisible.value = true
      saveStateStore.setRetrySchedule({ retryCount: retryAttempt, nextRetryAt: '' })
      saveStateStore.markError(String(error.userMessage || '检测到版本冲突，请先决定是否覆盖。'))
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

const activateChapter = async (chapterId) => {
  const nextChapterId = String(chapterId || '')
  if (!nextChapterId) return
  pendingChapterId.value = ''
  chapterDataStore.setActiveChapter(nextChapterId)
  workspaceStore.setLastOpenChapter(nextChapterId)
  await scrollSidebarToChapter(nextChapterId)
  await restoreViewportForChapter(nextChapterId)
  scheduleSessionSave()
}

onMounted(async () => {
  workspaceStore.setWorkContext(workId.value)
  saveStateStore.setSaveStatus('synced')
  window.addEventListener('offline', handleBrowserOffline)
  window.addEventListener('online', handleBrowserOnline)
  const [, session, chapters] = await Promise.all([loadWork(), loadSession(), loadChapters()])
  chapterDataStore.setChapters(chapters)
  loadCachedDrafts(chapters)
  const sessionChapterId = String(session?.last_open_chapter_id || session?.chapter_id || '')
  const matchedSessionChapter = chapters.find((chapter) => chapter.id === sessionChapterId)
  const initialChapterId = matchedSessionChapter?.id || chapters[0]?.id || ''
  if (initialChapterId) {
    await activateChapter(initialChapterId)
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

const handleSelectChapter = async (chapterId) => {
  const nextChapterId = String(chapterId || '')
  if (!nextChapterId || nextChapterId === chapterDataStore.activeChapterId) return
  if (saveStateStore.saveStatus === 'saving') {
    pendingChapterId.value = nextChapterId
    ElMessage.warning('正在同步数据，请稍候...')
    return
  }
  await activateChapter(nextChapterId)
}

const handleDraftChange = (content) => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId) return
  if (saveStateStore.nextRetryAt || saveStateStore.retryCount) {
    clearRetryTimer()
    saveStateStore.clearRetrySchedule()
  }
  chapterDataStore.updateChapterDraft(chapterId, content)
  workspaceStore.setLastOpenChapter(chapterId)
  writeCachedDraft(chapterId, content)
  saveStateStore.upsertDraft({
    chapterId,
    title: resolveChapterTitle(chapterId),
    content: String(content || ''),
    timestamp: Date.now()
  })
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

const handleTitleInput = (event) => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId) return
  if (saveStateStore.nextRetryAt || saveStateStore.retryCount) {
    clearRetryTimer()
    saveStateStore.clearRetrySchedule()
  }
  const nextTitle = parseEditableTitle(event?.target?.value)
  chapterDataStore.updateChapterTitleDraft(chapterId, nextTitle)
  workspaceStore.setLastOpenChapter(chapterId)
  writeCachedDraft(chapterId)
  saveStateStore.upsertDraft({
    chapterId,
    title: nextTitle,
    content: chapterDataStore.activeChapterContent,
    timestamp: Date.now()
  })
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

.studio-header {
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #ffffff;
  padding: 20px 24px;
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

.header-copy p {
  margin-top: 8px;
  color: #4b5563;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.studio-shell {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
}

.sidebar-column,
.editor-column {
  min-height: 0;
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

.editor-shell {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: start;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.chapter-title-input {
  display: block;
  width: min(560px, 100%);
  height: 44px;
  box-sizing: border-box;
  justify-self: center;
  align-self: start;
  flex: none;
  min-height: 44px;
  max-height: 44px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: #ffffff;
  padding: 0 14px;
  font-size: 16px;
  line-height: 44px;
  font-weight: 600;
  text-align: center;
  color: #111827;
  outline: none;
  appearance: none;
}

.chapter-title-input::placeholder {
  color: #9ca3af;
}

.chapter-title-input:focus {
  border-color: #dbeafe;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

.chapter-title-input:disabled {
  color: #9ca3af;
}

.editor-surface {
  flex: 1;
  min-height: 0;
  border-radius: 20px;
  background: #ffffff;
  padding: 0;
  display: flex;
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
}
</style>
