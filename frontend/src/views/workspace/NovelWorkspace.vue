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
          <div class="eyebrow">Writing Studio</div>
          <h1>纯文本写作页</h1>
          <p>当前作品：{{ workId }}</p>
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
            :chapters="chapterDataStore.chapters"
            :active-chapter-id="chapterDataStore.activeChapterId"
            :loading="chaptersLoading"
            @select="handleSelectChapter"
            @create="handleCreateChapter"
          />
        </div>
      </aside>

      <main class="editor-column">
        <div class="panel-card editor-card">
          <div class="panel-title-row">
            <h2>编辑区</h2>
            <span>宽边距正文区</span>
          </div>
          <p class="panel-description">V1 只保留纯文本编辑主线，富面板默认不展开。</p>
          <div class="editor-shell">
            <div class="editor-toolbar">
              <span>会话已加载：{{ workspaceStore.hydrated ? '是' : '否' }}</span>
              <span>光标：{{ workspaceStore.cursorPosition }}</span>
              <span>滚动：{{ workspaceStore.scrollTop }}</span>
            </div>
            <div class="editor-surface">
              <PureTextEditor
                ref="editorRef"
                :chapter-id="chapterDataStore.activeChapterId"
                :model-value="chapterDataStore.activeChapterContent"
                :chapter-title="activeChapterTitle"
                :placeholder="editorPlaceholder"
                @update:model-value="handleDraftChange"
                @cursor-change="handleCursorChange"
                @scroll-change="handleScrollChange"
              />
            </div>
          </div>
        </div>
      </main>

      <aside class="rail-column">
        <div class="rail-card">
          <div class="rail-icon">S</div>
          <div class="rail-icon">T</div>
          <div class="rail-icon">M</div>
          <p>右侧面板在 V1 默认隐藏，仅保留预留入口。</p>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { v1ChaptersApi, v1SessionsApi } from '@/api'
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
let sessionSaveTimer = null
let draftSyncTimer = null
let retryTimer = null
let isDraftSyncing = false
const DRAFT_SYNC_DELAY_MS = 2500
const RETRY_DELAYS_MS = [1000, 2000, 4000]
const conflictModalVisible = ref(false)
const conflictPayload = ref(null)

const workId = computed(() => String(route.params.id || ''))
const activeChapterTitle = computed(() => String(chapterDataStore.activeChapter?.title || '未命名章节'))
const activeWordCount = computed(() => countEffectiveCharacters(chapterDataStore.activeChapterContent))
const statusUpdatedAt = computed(() => String(saveStateStore.lastSyncedAt || workspaceStore.sessionUpdatedAt || ''))
const editorPlaceholder = computed(() => (
  chapterDataStore.activeChapterId ? '开始创作...' : '请先选择一个章节开始创作'
))
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
  const chapterTitle = String(conflictPayload.value?.chapterTitle || activeChapterTitle.value || '当前章节')
  return `${chapterTitle} 在云端已存在更新版本，请先决定是否覆盖。`
})

const buildDraftCacheKey = (chapterId) => `draft:${workId.value}:${String(chapterId || '')}`

const readCachedDraft = (chapterId) => localCache.get(buildDraftCacheKey(chapterId), null)

const writeCachedDraft = (chapterId, content) => {
  const chapter = chapterDataStore.chapters.find((item) => item.id === chapterId) || {}
  localCache.set(buildDraftCacheKey(chapterId), {
    workId: workId.value,
    chapterId,
    title: String(chapter.title || ''),
    content: String(content || ''),
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
      cachedDrafts.push({
        chapterId: chapter.id,
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
      return {
        chapterId: String(cached.chapterId || key.slice(prefix.length)),
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
          content: draft.content,
          expected_version: chapter.version
        })
        lastUpdatedAt = String(savedChapter?.updated_at || lastUpdatedAt)
        chapterDataStore.upsertChapter(savedChapter)
        const latestDraftContent = chapterDataStore.draftByChapterId[draft.chapterId]
        if (latestDraftContent === undefined || String(latestDraftContent) === String(draft.content || '')) {
          chapterDataStore.clearChapterDraft(draft.chapterId)
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
        chapterTitle: String(chapter?.title || '')
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
  await restoreViewportForChapter(nextChapterId)
  scheduleSessionSave()
}

onMounted(async () => {
  workspaceStore.setWorkContext(workId.value)
  saveStateStore.setSaveStatus('synced')
  window.addEventListener('offline', handleBrowserOffline)
  window.addEventListener('online', handleBrowserOnline)
  const [session, chapters] = await Promise.all([loadSession(), loadChapters()])
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

const handleCursorChange = ({ cursorPosition = 0 } = {}) => {
  workspaceStore.captureViewport({
    chapterId: chapterDataStore.activeChapterId,
    cursorPosition,
    scrollTop: workspaceStore.scrollTop
  })
  if (chapterDataStore.activeChapterId && chapterDataStore.draftByChapterId[chapterDataStore.activeChapterId] !== undefined) {
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
  if (chapterDataStore.activeChapterId && chapterDataStore.draftByChapterId[chapterDataStore.activeChapterId] !== undefined) {
    writeCachedDraft(chapterDataStore.activeChapterId, chapterDataStore.activeChapterContent)
  }
  scheduleSessionSave()
}

const handleCreateChapter = () => {
  ElMessage.warning('新建章节将在下一步接入到章节侧栏。')
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
  const chapter = chapterDataStore.chapters.find((item) => item.id === chapterId)
  saveStateStore.markSaving()
  try {
    const savedChapter = await v1ChaptersApi.forceOverride(chapterId, {
      content: latestContent,
      expected_version: Number(chapter?.version || 0)
    })
    chapterDataStore.upsertChapter(savedChapter)
    chapterDataStore.clearChapterDraft(chapterId)
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

.eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b7280;
}

.header-copy h1 {
  margin-top: 10px;
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
  grid-template-columns: 280px minmax(0, 1fr) 72px;
  gap: 16px;
}

.sidebar-column,
.editor-column,
.rail-column {
  min-height: 0;
}

.panel-card,
.rail-card {
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
  gap: 14px;
  margin-top: 18px;
  flex: 1;
  min-height: 0;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #6b7280;
}

.editor-surface {
  flex: 1;
  min-height: 0;
  border-radius: 20px;
  background: #f8fafc;
  padding: 20px;
  display: flex;
}

.rail-card {
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.rail-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #374151;
  font-size: 12px;
  font-weight: 700;
}

.rail-card p {
  margin-top: auto;
  font-size: 12px;
  line-height: 1.6;
  color: #6b7280;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
}

@media (max-width: 1120px) {
  .studio-shell {
    grid-template-columns: 1fr;
  }

  .rail-card p {
    writing-mode: initial;
    transform: none;
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
