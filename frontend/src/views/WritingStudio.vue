<template>
  <div class="writing-studio" :class="[themeClass, { 'writing-studio--focus': isFocusMode }]">
    <MultiChapterPanel
      :visible="multiChapterPanelVisible"
      :work-id="workId"
      :chapter-id="chapterDataStore.activeChapterId"
      @close="multiChapterPanelVisible = false"
      @open-review="handleMultiChapterOpenReview"
    />
    <VersionConflictModal
      :model-value="conflictModalVisible"
      :description="conflictDescription"
      :local-content="conflictLocalContent"
      :server-content="conflictServerContent"
      @cancel="handleConflictCancel"
      @discard="handleConflictDiscard"
      @override="handleConflictOverride"
    />
    <SelectionRewriteDiffModal
      :model-value="selectionRewriteStore.modalVisible"
      :source-text="selectionRewriteStore.selectionText"
      :edited-text="selectionRewriteStore.editedText"
      :diff-summary="selectionRewriteStore.diffSummary"
      :word-count-before="Number(selectionRewriteStore.candidate?.word_count_before || selectionRewriteStore.selectionText.length || 0)"
      :word-count-after="Number(selectionRewriteStore.candidate?.word_count_after || selectionRewriteStore.editedText.length || 0)"
      :mode-label="displaySelectionRewriteMode(selectionRewriteStore.candidate?.rewrite_mode)"
      :applying="selectionRewriteStore.applying"
      :waiting-user-action="selectionRewriteStore.status === 'pending'"
      :conflicted="selectionRewriteStore.status === 'conflicted'"
      :conflict-message="selectionRewriteStore.actionError"
      @update:model-value="handleSelectionRewriteModalVisibility"
      @update:edited-text="selectionRewriteStore.editedText = $event"
      @accept="handleSelectionRewriteAccept"
      @reject="handleSelectionRewriteReject"
      @reselect="handleReselectSelectionRewrite"
      @dismiss-conflict="selectionRewriteStore.clearError()"
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
          <button
            v-if="costEnabled && !isFocusMode"
            type="button"
            class="ink-button ink-button--ghost"
            data-test="cost-open"
            @click="openCostDashboard"
          >
            AI 用量与预算
          </button>
          <button
            v-if="analysisEnabled && !isFocusMode"
            type="button"
            class="ink-button ink-button--ghost"
            data-test="analysis-open"
            @click="openAnalysis"
          >
            创作分析
          </button>
          <button
            v-if="multiChapterEnabled && !isFocusMode"
            type="button"
            class="ink-button ink-button--ghost"
            :disabled="!chapterDataStore.activeChapterId"
            data-test="multi-chapter-open"
            @click="multiChapterPanelVisible = true"
          >
            准备多章新稿
          </button>
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
          <div
            v-show="!isFocusMode"
            ref="preferencePanelAnchorRef"
            class="preference-panel-anchor"
          >
            <button
              type="button"
              class="ink-button ink-button--ghost preference-toggle"
              data-test="writing-preference-toggle"
              @click="togglePreferencePanel"
            >
              写作偏好
            </button>
            <div
              v-if="preferencePanelVisible"
              class="preference-floating-panel"
              data-test="writing-preference-floating-panel"
            >
              <WritingPreferencePanel
                :preferences="editorPreferences"
                @update-preferences="handlePreferenceUpdate"
                @close="closePreferencePanel"
              />
            </div>
          </div>
          <FocusModeToggle
            :enabled="isFocusMode"
            @toggle="toggleFocusMode"
          />
          <el-button class="ink-el-button ink-el-button--primary studio-header-btn" v-show="!isFocusMode" type="primary" @click="goBack">返回书架</el-button>
        </div>
      </div>
    </header>

    <section
      class="studio-shell"
      :class="{
        'studio-shell--focus': isFocusMode,
        'studio-shell--drawer-open': Boolean(activeWorkspaceTab) && !isFocusMode
      }"
      :style="studioShellStyle"
    >
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
              <SelectionRewriteToolbar
                :visible="selectionRewriteToolbarVisible"
                :busy="selectionRewriteStore.loading"
                :polling="selectionRewriteStore.status === 'generating'"
                :floating-style="selectionRewriteToolbarStyle"
                :placement="selectionRewriteToolbarPlacement"
                @mode-select="handleSelectionRewriteMode"
                @clear-history="handleSelectionRewriteClearHistory"
              />
              <div
                v-if="mentionStore.featureEnabled && mentionStore.popupVisible"
                class="mention-popup-anchor"
                :style="mentionPopupStyle"
              >
                <MentionPopup
                  :visible="mentionStore.popupVisible"
                  :suggestions="mentionStore.suggestions"
                  :query="mentionStore.activeQuery"
                  :active-index="mentionStore.activeSuggestionIndex"
                  @select="handleMentionSuggestionSelect"
                  @create-character="handleMentionCreateCharacter"
                />
              </div>
              <PureTextEditor
                ref="editorRef"
                :chapter-id="chapterDataStore.activeChapterId"
                :model-value="chapterDataStore.activeChapterContent"
                :placeholder="editorPlaceholder"
                :font-family="editorPreferences.fontFamily"
                :font-size="editorPreferences.fontSize"
                :line-height="editorPreferences.lineHeight"
                :theme="preferenceStore.appTheme"
                :mentions="mentionStore.featureEnabled ? mentionStore.mentions : []"
                :mention-summary-by-id="mentionStore.mentionSummaryById"
                @update:model-value="handleDraftChange"
                @cursor-change="handleCursorChange"
                @selection-change="handleSelectionChange"
                @scroll-change="handleScrollChange"
                @mention-hover="handleMentionHover"
              />
            </div>
          </div>
        </div>
      </main>

      <aside v-show="!isFocusMode" class="right-workspace-column">
        <RightWorkspacePanel
          :model-value="activeWorkspaceTab"
          :dirty-tabs="assetDirtyTabs"
          :mobile="isMobileWorkspacePanel"
          @update:model-value="handleWorkspaceTabChange"
          @width-change="handleWorkspacePanelWidthChange"
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
              :active-chapter-id="chapterDataStore.activeChapterId"
              :chapters="chapterDataStore.chapters"
              @focus-area="handleAssetFocusArea"
            />
            <ForeshadowPanel
              v-else-if="activeTab === 'foreshadow'"
              ref="foreshadowPanelRef"
              :work-id="workId"
              :active-chapter-id="chapterDataStore.activeChapterId"
              :chapters="chapterDataStore.chapters"
              @focus-area="handleAssetFocusArea"
            />
            <CharacterPanel
              v-else-if="activeTab === 'character'"
              ref="characterPanelRef"
              :work-id="workId"
              :active-chapter-id="chapterDataStore.activeChapterId"
              @focus-area="handleAssetFocusArea"
            />
            <AIPanel
              v-else-if="activeTab === 'ai'"
              ref="aiPanelRef"
              mode="ai"
              :work-id="workId"
              :chapter-id="chapterDataStore.activeChapterId"
              :chapter-version="Number(chapterDataStore.activeChapter?.version || 0)"
              :chapter-options="chapterDataStore.chapters"
              :draft-chapter-ids="draftChapterIds"
              @open-review-tab="handleAIPanelOpenReviewTab"
            />
            <ReviewTab
              v-else-if="activeTab === 'review'"
              :work-id="workId"
              :chapter-id="chapterDataStore.activeChapterId"
              :chapter-version="Number(chapterDataStore.activeChapter?.version || 0)"
            />
          </template>
        </RightWorkspacePanel>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { v1ChaptersApi, v1WorksApi } from '@/api'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { useChapterDataStore } from '@/stores/useChapterDataStore'
import { useSaveStateStore } from '@/stores/useSaveStateStore'
import { usePreferenceStore } from '@/stores/preference'
import { useWritingAssetStore } from '@/stores/writingAsset'
import { countEffectiveCharacters } from '@/utils/textMetrics'
import AIPanel from '@/components/workspace/AIPanel.vue'
import CharacterPanel from '@/components/workspace/CharacterPanel.vue'
import ForeshadowPanel from '@/components/workspace/ForeshadowPanel.vue'
import FocusModeToggle from '@/components/workspace/FocusModeToggle.vue'
import ManualSyncButton from '@/components/workspace/ManualSyncButton.vue'
import MentionPopup from '@/components/workspace/MentionPopup.vue'
import MultiChapterPanel from '@/components/workspace/MultiChapterPanel.vue'
import OutlinePanel from '@/components/workspace/OutlinePanel.vue'
import ReviewTab from '@/components/workspace/ReviewTab.vue'
import RightWorkspacePanel from '@/components/workspace/RightWorkspacePanel.vue'
import TimelinePanel from '@/components/workspace/TimelinePanel.vue'
import WritingPreferencePanel from '@/components/workspace/WritingPreferencePanel.vue'
import ChapterSidebar from '@/components/workspace/ChapterSidebar.vue'
import ChapterTitleInput from '@/components/workspace/ChapterTitleInput.vue'
import PureTextEditor from '@/components/workspace/PureTextEditor.vue'
import SelectionRewriteDiffModal from '@/components/workspace/SelectionRewriteDiffModal.vue'
import SelectionRewriteToolbar from '@/components/workspace/SelectionRewriteToolbar.vue'
import StatusBar from '@/components/workspace/StatusBar.vue'
import VersionConflictModal from '@/components/workspace/VersionConflictModal.vue'
import { useMentionStore } from '@/stores/useMentionStore'
import { useSelectionRewriteStore } from '@/stores/useSelectionRewriteStore'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'

const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const chapterDataStore = useChapterDataStore()
const saveStateStore = useSaveStateStore()
const preferenceStore = usePreferenceStore()
const writingAssetStore = useWritingAssetStore()
const mentionStore = useMentionStore()
const selectionRewriteStore = useSelectionRewriteStore()
const multiChapterPanelVisible = ref(false)
const multiChapterEnabled = computed(() => isP2FeatureEnabled('enable_multi_chapter'))
const analysisEnabled = computed(() => isP2FeatureEnabled('enable_analysis_dashboard'))
const costEnabled = computed(() => isP2FeatureEnabled('enable_cost_dashboard'))
const chaptersLoading = ref(false)
const pendingChapterId = ref('')
const preferencePanelAnchorRef = ref(null)
const editorRef = ref(null)
const sidebarRef = ref(null)
const workTitleInputRef = ref(null)
const outlinePanelRef = ref(null)
const timelinePanelRef = ref(null)
const foreshadowPanelRef = ref(null)
const characterPanelRef = ref(null)
const aiPanelRef = ref(null)
const workTitle = ref('作品')
const workAuthor = ref('')
const workTitleEditing = ref(false)
const workTitleDraft = ref('')
const lastSelectionRewriteErrorKey = ref('')
let sessionSaveTimer = null
let draftSyncTimer = null
let retryTimer = null
let isDraftSyncing = false
const SELECTION_REWRITE_TOOLBAR_WIDTH = 320
const DRAFT_SYNC_DELAY_MS = 2500
const RETRY_DELAYS_MS = [1000, 2000, 4000]
const MOBILE_ASSET_BREAKPOINT = 760
const RIGHT_PANEL_MIN_WIDTH = 320
const RIGHT_PANEL_MAX_WIDTH = 760
const EDITOR_MIN_WIDTH = 620
const LEFT_COLUMN_WIDTH = 280
const SHELL_HORIZONTAL_PADDING = 40
const SHELL_GAP_WIDTH = 32
const activeWorkspaceTab = ref('')
const activeAssetFocusArea = ref('outline')
const isMobileWorkspacePanel = ref(false)
const rightWorkspacePanelWidth = ref(360)
const preferencePanelVisible = ref(false)
const lastEffectiveCountByChapterId = ref({})
const draftRevisionByChapterId = ref({})
const suppressDraftCaching = ref(false)
const selectionRewriteToolbarAnchor = ref({
  x: 0,
  y: 0,
  height: 0,
  containerWidth: 0
})

const workId = computed(() => String(route.params.id || ''))
const isFocusMode = computed(() => preferenceStore.focusMode)
const editorPreferences = computed(() => preferenceStore.editorPreferences)
const themeClass = computed(() => `writing-studio--${String(preferenceStore.appTheme || 'light')}`)
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
const selectionRewriteToolbarVisible = computed(() => (
  selectionRewriteStore.featureEnabled &&
  Boolean(chapterDataStore.activeChapterId) &&
  selectionRewriteStore.hasValidSelection &&
  !selectionRewriteStore.modalVisible
))
const selectionRewriteToolbarPlacement = computed(() => (
  Number(selectionRewriteToolbarAnchor.value.y || 0) < 96 ? 'below' : 'above'
))
const selectionRewriteToolbarStyle = computed(() => {
  const containerWidth = Number(selectionRewriteToolbarAnchor.value.containerWidth || 0)
  const minimumX = Math.min(SELECTION_REWRITE_TOOLBAR_WIDTH / 2, containerWidth / 2 || 0)
  const maximumX = Math.max(minimumX, containerWidth - (SELECTION_REWRITE_TOOLBAR_WIDTH / 2))
  const anchoredX = Number(selectionRewriteToolbarAnchor.value.x || 0)
  const clampedX = containerWidth
    ? Math.min(Math.max(anchoredX, minimumX), maximumX)
    : anchoredX
  const anchoredY = Number(selectionRewriteToolbarAnchor.value.y || 0)
  const anchoredHeight = Number(selectionRewriteToolbarAnchor.value.height || 0)
  return {
    left: `${Math.round(clampedX)}px`,
    top: `${Math.round(
      selectionRewriteToolbarPlacement.value === 'below'
        ? anchoredY + anchoredHeight
        : anchoredY
    )}px`
  }
})
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
  chapterDataStore.activeChapterId ? '开始输入正文...' : '请先选择章节后编辑'
))
const chapterTitlePlaceholder = computed(() => (
  chapterDataStore.activeChapterId ? '请输入章节标题' : '请选择章节'
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
  const prefix = `?${resolveChapterOrderIndex(chapter)}?`
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
    return '当前离线:内容已暂存本地,网络恢复后自动同步。'
  }
  return '当前离线:本章内容仅保存在本地。'
})
const statusDetail = computed(() => {
  if (conflictModalVisible.value) {
    return '检测到版本冲突,请先处理冲突。'
  }
  if (isOfflineMode.value && saveStateStore.hasPendingDrafts) {
    return `正在同步 ${saveStateStore.pendingQueue.length} 条草稿`
  }
  if (saveStateStore.saveStatus === 'saving' && saveStateStore.pendingQueue.length > 1) {
    return `正在同步 ${saveStateStore.pendingQueue.length} 条草稿`
  }
  if (saveStateStore.saveStatus === 'error' && saveStateStore.nextRetryAt) {
    return '同步失败,等待重试。'
  }
  if (showManualRetry.value) {
    return '同步失败,等待重试。'
  }
  return ''
})
const showManualRetry = computed(() => (
  saveStateStore.saveStatus === 'error' &&
  saveStateStore.hasPendingDrafts &&
  !saveStateStore.nextRetryAt &&
  !conflictModalVisible.value
))
const studioShellStyle = computed(() => ({
  '--right-workspace-panel-width': `${rightWorkspacePanelWidth.value}px`
}))
const mentionPopupStyle = computed(() => ({
  left: `${Number(mentionStore.popupPosition?.x || 24)}px`,
  top: `${Number(mentionStore.popupPosition?.y || 24)}px`
}))
const handleMentionHover = async (mention) => {
  const mentionId = String(mention?.mention_id || '')
  if (mentionId) await mentionStore.loadMentionSummary(mentionId)
}
const conflictDescription = computed(() => {
  const chapterTitle = String(
    conflictPayload.value?.chapterTitle ||
    chapterDataStore.activeChapterTitle ||
    buildChapterLabel(chapterDataStore.activeChapter, '') ||
    '当前章节'
  )
  return `${chapterTitle} 存在服务器新版本，请选择冲突处理方式。`
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

const getDraftRevision = (chapterId = chapterDataStore.activeChapterId) => {
  const id = String(chapterId || '')
  if (!id) return 0
  return Number(draftRevisionByChapterId.value[id] || 0)
}

const ensureDraftRevision = (chapterId = chapterDataStore.activeChapterId) => {
  const id = String(chapterId || '')
  if (!id || Object.prototype.hasOwnProperty.call(draftRevisionByChapterId.value, id)) {
    return getDraftRevision(id)
  }
  draftRevisionByChapterId.value = {
    ...draftRevisionByChapterId.value,
    [id]: 0
  }
  return 0
}

const bumpDraftRevision = (chapterId = chapterDataStore.activeChapterId) => {
  const id = String(chapterId || '')
  if (!id) return 0
  const nextRevision = getDraftRevision(id) + 1
  draftRevisionByChapterId.value = {
    ...draftRevisionByChapterId.value,
    [id]: nextRevision
  }
  return nextRevision
}

const syncSelectionRewriteContext = (targetChapterId = chapterDataStore.activeChapterId) => {
  const id = String(targetChapterId || '')
  const chapter = chapterDataStore.chapters.find((item) => item.id === id) || chapterDataStore.activeChapter || {}
  selectionRewriteStore.initializeContext({
    workId: workId.value,
    chapterId: id,
    chapterRevision: Number(chapter?.version || 0),
    draftRevision: ensureDraftRevision(id)
  })
}

const syncMentionContext = (
  targetChapterId = chapterDataStore.activeChapterId,
  targetChapterRevision = undefined
) => {
  const id = String(targetChapterId || '')
  const chapter = chapterDataStore.chapters.find((item) => item.id === id) || chapterDataStore.activeChapter || {}
  mentionStore.initializeContext({
    workId: workId.value,
    chapterId: id,
    chapterRevision: targetChapterRevision ?? Number(chapter?.version || 0)
  })
}

const displaySelectionRewriteMode = (mode) => ({
  expand: '扩写',
  rewrite: '重写',
  abbreviate: '缩写',
  polish: '润色',
  dialogue_opt: '对白优化',
  de_ai: '降低 AI 味'
}[String(mode || '')] || '')

const scrollSidebarToChapter = async (chapterId) => {
  await nextTick()
  sidebarRef.value?.scrollToChapter?.(chapterId)
}

const focusEditor = async () => {
  await nextTick()
  editorRef.value?.focusEditor?.()
}

const clearSelectionRewriteToolbarAnchor = () => {
  selectionRewriteToolbarAnchor.value = {
    x: 0,
    y: 0,
    height: 0,
    containerWidth: 0
  }
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

const resolveMentionPopupPosition = () => {
  const textarea = editorRef.value?.$el?.querySelector?.('textarea') || editorRef.value?.$el
  const fallbackX = 24
  const fallbackY = 24
  if (!textarea || typeof textarea.getBoundingClientRect !== 'function') {
    return { x: fallbackX, y: fallbackY }
  }
  const rect = textarea.getBoundingClientRect()
  return {
    x: Math.max(fallbackX, Math.min(48, Math.round(rect.width * 0.08))),
    y: Math.max(fallbackY, Math.min(56, Math.round(rect.height * 0.08)))
  }
}

const setEditorSelectionRange = (start = 0, end = start) => {
  const textarea = editorRef.value?.$el?.querySelector?.('textarea') || editorRef.value?.$el
  if (!textarea) return false
  textarea.selectionStart = Number(start || 0)
  textarea.selectionEnd = Number(end || 0)
  textarea.focus?.()
  return true
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

const scheduleDraftPersistence = () => {
  if (conflictModalVisible.value) return
  if (!navigator.onLine || isOfflineMode.value) {
    saveStateStore.markOffline()
  } else {
    saveStateStore.markSaving()
    scheduleDraftSync()
  }
  scheduleSessionSave()
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
    ElMessage.warning('正在保存中,请稍后再操作章节。')
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
    ElMessage.error('加载章节失败,请稍后重试。')
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
    console.error('保存编辑会话失败:', error)
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
        syncMentionContext(draft.chapterId, Number(savedChapter?.version || chapter.version || 0))
        await mentionStore.saveMentions(draft.content, {
          targetChapterId: draft.chapterId,
          chapterRevision: Number(savedChapter?.version || chapter.version || 0)
        })
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
      }, String(error.userMessage || '草稿与服务器版本冲突,请处理后再继续。'))
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
  ElMessage.warning('本地缓存空间不足,已自动清理较旧的暂存内容。')
}

const syncWorkspaceViewport = () => {
  isMobileWorkspacePanel.value = typeof window !== 'undefined' && window.innerWidth <= MOBILE_ASSET_BREAKPOINT
  if (isMobileWorkspacePanel.value) {
    rightWorkspacePanelWidth.value = RIGHT_PANEL_MIN_WIDTH
    return
  }
  rightWorkspacePanelWidth.value = clampRightWorkspacePanelWidth(rightWorkspacePanelWidth.value)
}

const clampRightWorkspacePanelWidth = (width) => {
  if (typeof window === 'undefined') {
    return Math.min(RIGHT_PANEL_MAX_WIDTH, Math.max(RIGHT_PANEL_MIN_WIDTH, Number(width || RIGHT_PANEL_MIN_WIDTH)))
  }
  const viewport = Number(window.innerWidth || 0)
  const maxByViewport = viewport - LEFT_COLUMN_WIDTH - EDITOR_MIN_WIDTH - SHELL_HORIZONTAL_PADDING - SHELL_GAP_WIDTH
  const dynamicMax = Math.min(RIGHT_PANEL_MAX_WIDTH, Math.max(RIGHT_PANEL_MIN_WIDTH, maxByViewport))
  return Math.min(dynamicMax, Math.max(RIGHT_PANEL_MIN_WIDTH, Number(width || RIGHT_PANEL_MIN_WIDTH)))
}

const handleWorkspacePanelWidthChange = (nextWidth) => {
  const numericWidth = Number(nextWidth)
  if (!Number.isFinite(numericWidth)) return
  rightWorkspacePanelWidth.value = clampRightWorkspacePanelWidth(numericWidth)
}

const saveFocusedAssetDraft = async () => {
  if (!activeWorkspaceTab.value) return false
  if (activeWorkspaceTab.value === 'outline') {
    await outlinePanelRef.value?.saveFocusedDraft?.(activeAssetFocusArea.value)
    return true
  }
  if (activeWorkspaceTab.value === 'timeline') {
    const mode = activeAssetFocusArea.value === 'timeline_reorder' ? 'reorder' : 'event'
    await timelinePanelRef.value?.saveFocusedDraft?.(mode)
    return true
  }
  if (activeWorkspaceTab.value === 'foreshadow') {
    await foreshadowPanelRef.value?.saveFocusedDraft?.()
    return true
  }
  if (activeWorkspaceTab.value === 'character') {
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
  const insideAssetPanel = Boolean(activeElement?.closest?.('.right-workspace-panel__body'))
  if (!insideEditor && !insideAssetPanel) return
  event.preventDefault()
  if (insideEditor) {
    await flushCurrentDraftNow()
    await persistSessionNow()
    return
  }
  await saveFocusedAssetDraft()
}

const handleMentionPopupKeyboard = async (event) => {
  if (!mentionStore.popupVisible || event?.isComposing) return
  if (event?.key === 'ArrowDown') {
    event.preventDefault()
    mentionStore.moveActiveSuggestion(1)
    return
  }
  if (event?.key === 'ArrowUp') {
    event.preventDefault()
    mentionStore.moveActiveSuggestion(-1)
    return
  }
  if (event?.key === 'Enter') {
    const activeSuggestion = mentionStore.getActiveSuggestion()
    if (!activeSuggestion) return
    event.preventDefault()
    await handleMentionSuggestionSelect(activeSuggestion)
  }
}

const activateChapter = async (chapterId) => {
  const nextChapterId = String(chapterId || '')
  if (!nextChapterId) return
  pendingChapterId.value = ''
  chapterDataStore.setActiveChapter(nextChapterId)
  ensureDraftRevision(nextChapterId)
  syncSelectionRewriteContext(nextChapterId)
  syncMentionContext(nextChapterId)
  await mentionStore.loadMentions(nextChapterId)
  syncChapterWordBaseline(nextChapterId)
  workspaceStore.setLastOpenChapter(nextChapterId)
  await scrollSidebarToChapter(nextChapterId)
  await restoreViewportForChapter(nextChapterId)
  scheduleSessionSave()
}

onMounted(async () => {
  preferenceStore.hydrate()
  syncWorkspaceViewport()
  saveStateStore.setSaveStatus('synced')
  saveStateStore.clearConflict()
  saveStateStore.clearRetrySchedule()
  window.addEventListener('offline', handleBrowserOffline)
  window.addEventListener('online', handleBrowserOnline)
  window.addEventListener('inktrace-cache-pruned', handleCachePruned)
  window.addEventListener('keydown', handleEditorSaveShortcut)
  window.addEventListener('keydown', handleMentionPopupKeyboard)
  window.addEventListener('keydown', handlePreferencePanelEscape)
  window.addEventListener('resize', syncWorkspaceViewport)
  document.addEventListener('pointerdown', handlePreferencePanelPointerDown)
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
  window.removeEventListener('keydown', handleMentionPopupKeyboard)
  window.removeEventListener('keydown', handlePreferencePanelEscape)
  window.removeEventListener('resize', syncWorkspaceViewport)
  document.removeEventListener('pointerdown', handlePreferencePanelPointerDown)
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

const openAnalysis = () => {
  router.push(`/works/${encodeURIComponent(workId.value)}/analysis`)
}

const openCostDashboard = () => {
  router.push(`/works/${encodeURIComponent(workId.value)}/cost`)
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

const closePreferencePanel = () => {
  preferencePanelVisible.value = false
}

const handlePreferencePanelPointerDown = (event) => {
  if (!preferencePanelVisible.value) return
  const anchor = preferencePanelAnchorRef.value
  const target = event?.target
  if (anchor && target && !anchor.contains(target)) {
    closePreferencePanel()
  }
}

const handlePreferencePanelEscape = (event) => {
  if (event?.key !== 'Escape') return
  if (mentionStore.popupVisible) {
    mentionStore.closePopup()
  }
  if (preferencePanelVisible.value) {
    closePreferencePanel()
  }
}

const handlePreferenceUpdate = (patch = {}) => {
  preferenceStore.updateWritingPreferences(patch)
}

const handleWorkspaceTabChange = (tabKey) => {
  const nextKey = String(tabKey || '')
  activeAssetFocusArea.value = String(nextKey || activeWorkspaceTab.value || 'outline')
  activeWorkspaceTab.value = nextKey
}

const handleAIPanelOpenReviewTab = () => {
  activeAssetFocusArea.value = 'review'
  activeWorkspaceTab.value = 'review'
}

const handleMultiChapterOpenReview = () => {
  multiChapterPanelVisible.value = false
  handleAIPanelOpenReviewTab()
}

const handleAssetFocusArea = (area) => {
  activeAssetFocusArea.value = String(area || activeWorkspaceTab.value || 'outline')
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
    ElMessage.success('作品标题已更新')
  } catch (error) {
    console.error('更新作品标题失败:', error)
    workTitleEditing.value = false
    workTitleDraft.value = currentTitle
    ElMessage.error('更新作品标题失败,请稍后重试。')
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
  ElMessage.warning('请输入有效章节序号。')
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
  bumpDraftRevision(chapterId)
  syncSelectionRewriteContext(chapterId)
  selectionRewriteStore.clearSelection()
  workspaceStore.setLastOpenChapter(chapterId)
  writeCachedDraft(chapterId, content)
  scheduleDraftPersistence()
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
  syncMentionContext()
  mentionStore.inspectTrigger({
    content: chapterDataStore.activeChapterContent,
    cursorPosition,
    popupPosition: resolveMentionPopupPosition()
  })
  scheduleSessionSave()
}

const handleSelectionChange = ({
  text = '',
  start = 0,
  end = 0,
  anchorX = 0,
  anchorY = 0,
  anchorHeight = 0,
  containerWidth = 0
} = {}) => {
  syncSelectionRewriteContext()
  selectionRewriteStore.setSelection({
    text,
    start,
    end
  })
  if (!text || end <= start) {
    clearSelectionRewriteToolbarAnchor()
    return
  }
  selectionRewriteToolbarAnchor.value = {
    x: Number(anchorX || 0),
    y: Number(anchorY || 0),
    height: Number(anchorHeight || 0),
    containerWidth: Number(containerWidth || 0)
  }
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

const handleSelectionRewriteMode = async (mode) => {
  try {
    syncSelectionRewriteContext()
    await selectionRewriteStore.createRewrite(mode)
  } catch (error) {
    ElMessage.error(selectionRewriteStore.actionError || '选区改写生成失败,请稍后重试。')
  }
}

const handleSelectionRewriteModalVisibility = (visible) => {
  if (visible) return
  selectionRewriteStore.clearModalState()
}

const handleUndoSelectionRewriteApply = async () => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId) return
  const restored = selectionRewriteStore.undoLastApply()
  if (!restored) return
  bumpDraftRevision(chapterId)
  syncSelectionRewriteContext(chapterId)
  syncChapterWordBaseline(chapterId, chapterDataStore.activeChapterContent)
  workspaceStore.setLastOpenChapter(chapterId)
  writeCachedDraft(chapterId, chapterDataStore.activeChapterContent)
  scheduleDraftPersistence()
  await nextTick()
}

const handleRetrySelectionRewrite = async () => {
  try {
    await selectionRewriteStore.retryLastRewrite()
  } catch (error) {
    ElMessage.error(selectionRewriteStore.actionError || '选区改写生成失败,请稍后重试。')
  }
}

const handleReselectSelectionRewrite = async () => {
  selectionRewriteStore.activeRewriteId = ''
  selectionRewriteStore.requestId = ''
  selectionRewriteStore.status = ''
  selectionRewriteStore.candidate = null
  selectionRewriteStore.clearSelection()
  selectionRewriteStore.clearModalState()
  selectionRewriteStore.clearError()
  await nextTick()
  await focusEditor()
}

const handleSelectionRewriteClearHistory = async () => {
  try {
    const result = await selectionRewriteStore.clearChapterHistory()
    ElMessage.success(`已清除 ${Number(result?.cleared_count || 0)} 条历史改写。`)
  } catch (error) {
    ElMessage.error(selectionRewriteStore.actionError || '清除历史改写失败,请稍后重试。')
  }
}

const handleSelectionRewriteAccept = async ({ finalText = '' } = {}) => {
  const chapterId = String(chapterDataStore.activeChapterId || '')
  if (!chapterId) return
  try {
    selectionRewriteStore.editedText = String(finalText || selectionRewriteStore.editedText || '')
    await selectionRewriteStore.applyCurrentRewrite()
    bumpDraftRevision(chapterId)
    syncSelectionRewriteContext(chapterId)
    syncChapterWordBaseline(chapterId, chapterDataStore.activeChapterContent)
    workspaceStore.setLastOpenChapter(chapterId)
    writeCachedDraft(chapterId, chapterDataStore.activeChapterContent)
    selectionRewriteStore.clearSelection()
    scheduleDraftPersistence()
    ElMessage.success({
      duration: 5000,
      message: h('span', { class: 'selection-rewrite-apply-toast' }, [
        h('span', '选区改写已应用。'),
        h('button', {
          type: 'button',
          class: 'selection-rewrite-undo-button',
          onClick: () => handleUndoSelectionRewriteApply()
        }, '撤销')
      ])
    })
  } catch (error) {
    ElMessage.error(selectionRewriteStore.actionError || '选区改写应用失败,请重新尝试。')
  }
}

const handleSelectionRewriteReject = async () => {
  try {
    await selectionRewriteStore.rejectCurrentRewrite()
    selectionRewriteStore.clearSelection()
    ElMessage.info({
      duration: 2000,
      message: '已拒绝'
    })
  } catch (error) {
    ElMessage.error(selectionRewriteStore.actionError || '选区改写拒绝失败,请稍后重试。')
  }
}

watch(
  () => [
    String(selectionRewriteStore.activeRewriteId || ''),
    String(selectionRewriteStore.status || ''),
    String(selectionRewriteStore.actionError || '')
  ],
  ([rewriteId, rewriteStatus, rewriteError]) => {
    if (!rewriteId || !rewriteError) return
    if (!['failed', 'conflicted', 'expired'].includes(rewriteStatus)) return
    const nextKey = `${rewriteId}:${rewriteStatus}:${rewriteError}`
    if (lastSelectionRewriteErrorKey.value === nextKey) return
    lastSelectionRewriteErrorKey.value = nextKey
    if (rewriteStatus === 'failed') {
      ElMessage.error({
        duration: 5000,
        message: h('span', { class: 'selection-rewrite-error-toast' }, [
          h('span', rewriteError),
          h('button', {
            type: 'button',
            class: 'selection-rewrite-retry-button',
            onClick: () => handleRetrySelectionRewrite()
          }, '重试'),
          h('button', {
            type: 'button',
            class: 'selection-rewrite-cancel-button',
            onClick: () => {
              selectionRewriteStore.clearError()
            }
          }, '取消')
        ])
      })
      return
    }
    if (rewriteStatus === 'conflicted') return
    ElMessage.error(rewriteError)
  }
)

const handleMentionSuggestionSelect = async (suggestion) => {
  const label = `@${String(suggestion?.entity_name || '')}`
  const range = mentionStore.triggerRange || { start: 0, end: 0 }
  setEditorSelectionRange(range.start, range.end)
  mentionStore.suppressNextTriggerInspection()
  const inserted = editorRef.value?.insertPlainTextAtSelection?.(label)
  if (!inserted) return
  mentionStore.registerInsertedMention(suggestion, inserted)
  await nextTick()
  await focusEditor()
}

const handleMentionCreateCharacter = async () => {
  mentionStore.closePopup()
  activeWorkspaceTab.value = 'character'
  activeAssetFocusArea.value = 'character'
  await nextTick()
  characterPanelRef.value?.startCreate?.()
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
    ElMessage.success('章节已创建')
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
    ElMessage.success('章节标题已更新')
  } catch (error) {
    console.error('重命名章节失败:', error)
  }
}

const handleDeleteChapter = async (chapterId) => {
  const id = String(chapterId || '')
  if (!id || blockSidebarMutation()) return
  if (!window.confirm('确认删除该章节吗?')) return
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
    ElMessage.success('章节已删除')
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
    ElMessage.success('章节顺序已更新')
  } catch (error) {
    console.error('调整章节顺序失败:', error)
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
  ElMessage.success('已应用服务器版本并清除本地冲突。')
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
    ElMessage.success('已覆盖服务器版本并完成同步。')
    if (saveStateStore.pendingQueue.length) {
      scheduleDraftSync()
    }
  } catch (error) {
    const message = String(error?.userMessage || error?.message || '覆盖保存失败')
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
  --studio-bg: var(--ink-bg-app);
  --studio-bg-focus: var(--ink-bg-app);
  --studio-card-bg: var(--ink-surface-1);
  --studio-border: var(--ink-border);
  --studio-title: var(--ink-text-primary);
  --studio-text: var(--ink-text-secondary);
  --studio-muted: var(--ink-text-muted);
  --studio-input-bg: var(--ink-surface-1);
  --studio-button-bg: var(--ink-surface-1);

  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px 20px 24px;
  gap: 16px;
  background: var(--studio-bg);
}

.writing-studio--focus {
  background: var(--studio-bg-focus);
}

.writing-studio--dark {
  --studio-bg: var(--ink-bg-app);
  --studio-bg-focus: var(--ink-bg-app);
  --studio-card-bg: var(--ink-surface-1);
  --studio-border: var(--ink-border);
  --studio-title: var(--ink-text-primary);
  --studio-text: var(--ink-text-secondary);
  --studio-muted: var(--ink-text-muted);
  --studio-input-bg: var(--ink-surface-1);
  --studio-button-bg: var(--ink-surface-1);
}

.writing-studio--warm {
  --studio-bg: var(--ink-bg-app);
  --studio-bg-focus: var(--ink-bg-app);
  --studio-card-bg: var(--ink-surface-1);
  --studio-border: var(--ink-border);
  --studio-title: var(--ink-text-primary);
  --studio-text: var(--ink-text-secondary);
  --studio-muted: var(--ink-text-muted);
  --studio-input-bg: var(--ink-surface-1);
  --studio-button-bg: var(--ink-surface-1);
}

.studio-header {
  border: 1px solid var(--studio-border);
  border-radius: 24px;
  background: var(--studio-card-bg);
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
  color: var(--studio-title);
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
  color: var(--studio-title);
  cursor: pointer;
  text-align: left;
}

.work-title-input {
  width: min(520px, 100%);
  border: 1px solid var(--studio-border);
  border-radius: 14px;
  background: var(--studio-input-bg);
  padding: 10px 14px;
  font-size: 20px;
  font-weight: 600;
  color: var(--studio-title);
  outline: none;
}

.work-title-input:focus {
  border-color: var(--ink-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ink-accent) 24%, transparent);
}

.header-copy p {
  margin-top: 8px;
  color: var(--studio-text);
}

.header-copy--muted p {
  color: var(--studio-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-actions :deep(.studio-header-btn.el-button) {
  min-width: 112px;
}

.preference-toggle {
  min-width: 96px;
}

.preference-toggle:hover {
  color: var(--ink-accent);
}

.preference-panel-anchor {
  position: relative;
}

.preference-floating-panel {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  z-index: 30;
  width: min(320px, calc(100vw - 32px));
}

.studio-shell {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 48px;
  gap: 16px;
  width: 100%;
  overflow: hidden;
}

.studio-shell--drawer-open {
  grid-template-columns: 280px minmax(0, 1fr) var(--right-workspace-panel-width, 360px);
}

.studio-shell--focus {
  grid-template-columns: minmax(0, 1fr);
}

.sidebar-column,
.editor-column,
.right-workspace-column {
  min-width: 0;
  min-height: 0;
}

.editor-column--focus {
  max-width: 960px;
  width: min(100%, 960px);
  margin: 0 auto;
}

.panel-card {
  height: 100%;
  border: 1px solid var(--studio-border);
  border-radius: 24px;
  background: var(--studio-card-bg);
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
  color: var(--studio-title);
}

.panel-title-row span {
  font-size: 12px;
  color: var(--studio-muted);
}

.panel-description {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--studio-muted);
}

.editor-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.editor-card--focus {
  border-color: var(--ink-accent-soft);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
}

.editor-shell {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: start;
  gap: 8px;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.editor-surface {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  border-radius: 20px;
  background: var(--studio-card-bg);
  padding: 0;
  display: flex;
}

.mention-popup-anchor {
  position: absolute;
  z-index: 20;
}

.right-workspace-column {
  width: 100%;
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

  .preference-panel-anchor {
    width: 100%;
  }

  .preference-floating-panel {
    position: fixed;
    left: 16px;
    right: 16px;
    bottom: 16px;
    top: auto;
    width: auto;
  }

  .right-workspace-column {
    width: 100%;
  }
}
</style>


