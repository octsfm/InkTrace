<template>
  <section class="outline-panel" data-panel="outline">
    <header class="outline-header">
      <div class="outline-mode-tabs" role="tablist" aria-label="大纲视图切换">
        <button
          type="button"
          class="outline-mode-tab"
          :class="{ active: currentMode === 'work' }"
          data-testid="outline-mode-work"
          @click="requestModeSwitch('work')"
        >
          作品大纲
        </button>
        <button
          type="button"
          class="outline-mode-tab"
          :class="{ active: currentMode === 'chapter' }"
          data-testid="outline-mode-chapter"
          @click="requestModeSwitch('chapter')"
        >
          章节大纲
        </button>
      </div>
      <div class="outline-header-actions">
        <button
          v-if="currentMode === 'work'"
          type="button"
          class="ghost-button"
          data-testid="outline-import-trigger"
          @click="openImportModal"
        >
          导入
        </button>
        <span v-if="currentDirty" class="dirty-indicator">未保存</span>
      </div>
    </header>

    <div class="outline-editor-shell">
      <template v-if="currentMode === 'work'">
        <p class="outline-description">`content_text` 是唯一真源，树结构仅作为派生缓存保存。</p>
        <textarea
          class="outline-textarea"
          :value="draftText"
          placeholder="在这里输入整本作品的大纲。"
          data-testid="work-outline-text"
          @input="handleInput"
          @focus="$emit('focus-area', 'outline')"
        />
      </template>

      <template v-else>
        <p v-if="activeChapterId" class="chapter-outline-caption">当前章节：{{ activeChapterId }}</p>
        <div v-if="!activeChapterId" class="outline-empty-state">请先选择一个章节，再编辑章节大纲。</div>
        <textarea
          v-else
          class="outline-textarea chapter-outline-textarea"
          :value="chapterDraftText"
          placeholder="在这里输入当前章节的细纲。"
          data-testid="chapter-outline-text"
          @input="handleChapterInput"
          @focus="$emit('focus-area', 'chapter_outline')"
        />
      </template>
    </div>

    <footer class="outline-footer">
      <span class="save-status">{{ currentMode === 'work' ? saveStatusLabel : chapterSaveStatusLabel }}</span>
      <button
        type="button"
        class="save-button"
        :disabled="currentMode === 'chapter' ? (!activeChapterId || chapterSaveStatus === 'saving') : saveStatus === 'saving'"
        @click="currentMode === 'work' ? handleSave() : handleChapterSave()"
      >
        {{ currentMode === 'work' ? '保存作品大纲' : '保存章节大纲' }}
      </button>
    </footer>

    <section v-if="modeSwitchGuardVisible" class="mode-switch-guard">
      <p>当前编辑区存在未保存内容，切换前请选择处理方式。</p>
      <div class="mode-switch-guard-actions">
        <button type="button" class="save-button" @click="handleGuardSave">保存并切换</button>
        <button type="button" class="ghost-button" @click="handleGuardDiscard">放弃并切换</button>
        <button type="button" class="ghost-button" @click="handleGuardCancel">取消</button>
      </div>
    </section>

    <OutlineImportModal
      :visible="importModalVisible"
      :current-draft-text="draftText"
      @close="closeImportModal"
      @import="handleImportApply"
    />

    <AssetConflictModal
      :model-value="conflictVisible"
      :description="conflictDescription"
      :local-content="localConflictContent"
      :server-content="serverContent"
      @cancel="assetStore.clearAssetConflict"
      @discard="handleDiscardConflict"
      @override="handleOverrideConflict"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import { mergeOutlineImportText } from '@/utils/outlineImport'
import { useWritingAssetStore } from '@/stores/writingAsset'
import AssetConflictModal from './AssetConflictModal.vue'
import OutlineImportModal from './OutlineImportModal.vue'

const props = defineProps({
  workId: {
    type: String,
    default: ''
  },
  activeChapterId: {
    type: String,
    default: ''
  }
})

defineEmits(['focus-area'])

const assetStore = useWritingAssetStore()
const currentMode = ref('work')
const pendingModeSwitch = ref('')
const importModalVisible = ref(false)
const draftText = ref('')
const chapterDraftText = ref('')
const saveStatusLabelMap = {
  idle: '待保存',
  dirty: '待保存',
  saving: '保存中',
  synced: '已保存',
  error: '保存失败',
  conflict: '存在冲突'
}

const assetKey = 'work_outline:work'
const draft = computed(() => assetStore.assetDrafts[assetKey] || null)
const outline = computed(() => assetStore.workOutline || null)
const activeChapterId = computed(() => String(props.activeChapterId || ''))
const chapterAssetKey = computed(() => (activeChapterId.value ? `chapter_outline:${activeChapterId.value}` : ''))
const chapterDraft = computed(() => assetStore.assetDrafts[chapterAssetKey.value] || null)
const chapterOutline = computed(() => assetStore.chapterOutlines[activeChapterId.value] || null)
const isDirty = computed(() => assetStore.dirtyAssetKeys.includes(assetKey))
const chapterOutlineDirty = computed(() => Boolean(chapterAssetKey.value && assetStore.dirtyAssetKeys.includes(chapterAssetKey.value)))
const currentDirty = computed(() => (currentMode.value === 'work' ? isDirty.value : chapterOutlineDirty.value))
const saveStatus = computed(() => assetStore.getAssetSaveStatus('work_outline', 'work'))
const chapterSaveStatus = computed(() => assetStore.getAssetSaveStatus('chapter_outline', activeChapterId.value))
const saveStatusLabel = computed(() => saveStatusLabelMap[saveStatus.value] || saveStatusLabelMap.idle)
const chapterSaveStatusLabel = computed(() => saveStatusLabelMap[chapterSaveStatus.value] || saveStatusLabelMap.idle)
const modeSwitchGuardVisible = computed(() => Boolean(pendingModeSwitch.value))
const conflictAssetType = computed(() => String(assetStore.assetConflictPayload?.asset_type || ''))
const conflictVisible = computed(() => (
  conflictAssetType.value === 'work_outline' || conflictAssetType.value === 'chapter_outline'
))
const conflictDescription = computed(() => (
  conflictAssetType.value === 'chapter_outline'
    ? '章节大纲已在其他位置被修改，请先处理冲突，再决定是否清除本地草稿。'
    : '作品大纲已在其他位置被修改，请先处理冲突，再决定是否清除本地草稿。'
))
const localConflictContent = computed(() => (
  conflictAssetType.value === 'chapter_outline' ? chapterDraftText.value : draftText.value
))
const serverContent = computed(() => String(assetStore.assetConflictPayload?.server_content || ''))

const syncFromStore = () => {
  draftText.value = String(
    draft.value?.payload?.content_text ??
    outline.value?.content_text ??
    ''
  )
}

const syncChapterFromStore = () => {
  chapterDraftText.value = String(
    chapterDraft.value?.payload?.content_text ??
    chapterOutline.value?.content_text ??
    ''
  )
}

const buildSavePayload = (content = draftText.value, overrides = {}) => ({
  content_text: String(content ?? ''),
  content_tree_json: outline.value?.content_tree_json ?? [],
  expected_version: outline.value?.version ?? 1,
  ...overrides
})

const buildChapterSavePayload = (content = chapterDraftText.value, overrides = {}) => ({
  content_text: String(content ?? ''),
  content_tree_json: chapterOutline.value?.content_tree_json ?? [],
  expected_version: chapterOutline.value?.version ?? 1,
  ...overrides
})

const applyModeSwitch = (mode) => {
  currentMode.value = mode === 'chapter' ? 'chapter' : 'work'
  pendingModeSwitch.value = ''
}

const requestModeSwitch = (mode) => {
  const nextMode = mode === 'chapter' ? 'chapter' : 'work'
  if (nextMode === currentMode.value) return
  if (currentDirty.value) {
    pendingModeSwitch.value = nextMode
    return
  }
  applyModeSwitch(nextMode)
}

const openImportModal = () => {
  if (currentMode.value !== 'work') return
  importModalVisible.value = true
}

const closeImportModal = () => {
  importModalVisible.value = false
}

const handleImportApply = ({ content = '', mode = 'replace' } = {}) => {
  const merged = mergeOutlineImportText(draftText.value, content, mode)
  draftText.value = merged
  assetStore.writeAssetDraft('work_outline', 'work', buildSavePayload(merged))
  closeImportModal()
}

const handleInput = (event) => {
  draftText.value = String(event?.target?.value ?? '')
  assetStore.writeAssetDraft('work_outline', 'work', buildSavePayload())
}

const handleChapterInput = (event) => {
  if (!activeChapterId.value) return
  chapterDraftText.value = String(event?.target?.value ?? '')
  assetStore.writeAssetDraft('chapter_outline', activeChapterId.value, buildChapterSavePayload())
}

const handleSave = async () => {
  if (!assetStore.assetDrafts[assetKey]) {
    assetStore.writeAssetDraft('work_outline', 'work', buildSavePayload())
  }
  try {
    await assetStore.saveWorkOutline()
    return true
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
    return false
  }
}

const handleChapterSave = async () => {
  if (!activeChapterId.value) return false
  if (!assetStore.assetDrafts[chapterAssetKey.value]) {
    assetStore.writeAssetDraft('chapter_outline', activeChapterId.value, buildChapterSavePayload())
  }
  try {
    await assetStore.saveChapterOutline(activeChapterId.value)
    return true
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
    return false
  }
}

const discardWorkLocal = async () => {
  assetStore.discardAssetDraft('work_outline', 'work')
  if (props.workId) {
    await assetStore.loadWorkOutline(props.workId)
  }
  syncFromStore()
}

const discardChapterLocal = async () => {
  if (!activeChapterId.value) return
  assetStore.discardAssetDraft('chapter_outline', activeChapterId.value)
  await assetStore.loadChapterOutline(activeChapterId.value)
  syncChapterFromStore()
}

const handleGuardSave = async () => {
  const ok = currentMode.value === 'work'
    ? await handleSave()
    : await handleChapterSave()
  if (ok && pendingModeSwitch.value) {
    applyModeSwitch(pendingModeSwitch.value)
  }
}

const handleGuardDiscard = async () => {
  if (currentMode.value === 'work') {
    await discardWorkLocal()
  } else {
    await discardChapterLocal()
  }
  if (pendingModeSwitch.value) {
    applyModeSwitch(pendingModeSwitch.value)
  }
}

const handleGuardCancel = () => {
  pendingModeSwitch.value = ''
}

const handleOverrideConflict = async () => {
  if (conflictAssetType.value === 'chapter_outline' && activeChapterId.value) {
    assetStore.writeAssetDraft('chapter_outline', activeChapterId.value, buildChapterSavePayload(chapterDraftText.value, { force_override: true }))
    try {
      await assetStore.saveChapterOutline(activeChapterId.value)
      assetStore.clearAssetConflict()
    } catch (error) {
      if (!assetStore.assetConflictPayload) {
        throw error
      }
    }
    return
  }
  assetStore.writeAssetDraft('work_outline', 'work', buildSavePayload(draftText.value, { force_override: true }))
  try {
    await assetStore.saveWorkOutline()
    assetStore.clearAssetConflict()
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleDiscardConflict = async () => {
  if (conflictAssetType.value === 'chapter_outline') {
    assetStore.clearAssetConflict()
    await discardChapterLocal()
    return
  }
  assetStore.clearAssetConflict()
  await discardWorkLocal()
}

onMounted(async () => {
  if (props.workId) {
    assetStore.setWorkContext(props.workId)
    assetStore.readAssetDraft('work_outline', 'work')
    if (!assetStore.workOutline) {
      await assetStore.loadWorkOutline(props.workId)
    }
  }
  if (activeChapterId.value) {
    assetStore.readAssetDraft('chapter_outline', activeChapterId.value)
    if (!assetStore.chapterOutlines[activeChapterId.value]) {
      await assetStore.loadChapterOutline(activeChapterId.value)
    }
  }
  syncFromStore()
  syncChapterFromStore()
})

watch(
  () => [outline.value?.content_text, draft.value?.payload?.content_text],
  syncFromStore
)

watch(
  () => activeChapterId.value,
  async (nextChapterId) => {
    if (!nextChapterId) {
      chapterDraftText.value = ''
      return
    }
    assetStore.readAssetDraft('chapter_outline', nextChapterId)
    if (!assetStore.chapterOutlines[nextChapterId]) {
      await assetStore.loadChapterOutline(nextChapterId)
    }
    syncChapterFromStore()
  }
)

watch(
  () => [chapterOutline.value?.content_text, chapterDraft.value?.payload?.content_text],
  syncChapterFromStore
)

defineExpose({
  saveFocusedDraft(area = 'outline') {
    return area === 'chapter_outline' ? handleChapterSave() : handleSave()
  },
  discardFocusedDraft(area = 'outline') {
    return area === 'chapter_outline' ? discardChapterLocal() : discardWorkLocal()
  }
})
</script>

<style scoped>
.outline-panel {
  display: grid;
  gap: 14px;
}

.outline-header,
.outline-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.outline-mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.outline-mode-tab,
.ghost-button,
.save-button {
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
}

.outline-mode-tab,
.ghost-button {
  background: #f3f4f6;
  color: #111827;
}

.outline-mode-tab.active {
  background: #dbeafe;
  color: #1d4ed8;
}

.save-button {
  background: #111827;
  color: #ffffff;
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.outline-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.outline-editor-shell {
  display: grid;
  gap: 12px;
}

.outline-description,
.chapter-outline-caption,
.outline-empty-state,
.save-status,
.mode-switch-guard p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.outline-empty-state {
  border: 1px dashed #d1d5db;
  border-radius: 16px;
  background: #f8fafc;
  padding: 16px;
}

.dirty-indicator {
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
}

.outline-textarea {
  min-height: 320px;
  resize: vertical;
  border: 1px solid #d1d5db;
  border-radius: 16px;
  padding: 14px;
  color: #111827;
  font: inherit;
  line-height: 1.7;
}

.chapter-outline-textarea {
  min-height: 240px;
}

.mode-switch-guard {
  display: grid;
  gap: 12px;
  border: 1px solid #fde68a;
  border-radius: 16px;
  background: #fffbeb;
  padding: 14px;
}

.mode-switch-guard-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 760px) {
  .outline-header,
  .outline-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .outline-header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .outline-mode-tabs {
    width: 100%;
  }
}
</style>
