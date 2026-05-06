<template>
  <section class="outline-panel" data-panel="outline">
    <header class="outline-header">
      <div>
        <h3>Work Outline</h3>
        <p>content_text is the only source of truth. Tree data is saved only as a derived cache.</p>
      </div>
      <span v-if="isDirty" class="dirty-indicator">Unsaved</span>
    </header>

    <textarea
      class="outline-textarea"
      :value="draftText"
      placeholder="Write the full-book outline here."
      data-testid="work-outline-text"
      @input="handleInput"
      @focus="$emit('focus-area', 'outline')"
    />

    <footer class="outline-footer">
      <span class="save-status">{{ saveStatus }}</span>
      <button type="button" class="save-button" :disabled="saveStatus === 'saving'" @click="handleSave">
        Save Outline
      </button>
    </footer>

    <section class="chapter-outline-section">
      <header class="outline-header">
        <div>
          <h3>Chapter Outline</h3>
          <p>The current chapter outline switches with the active chapter.</p>
        </div>
        <span v-if="chapterOutlineDirty" class="dirty-indicator">Unsaved</span>
      </header>
      <textarea
        class="outline-textarea chapter-outline-textarea"
        :value="chapterDraftText"
        placeholder="Write the current chapter outline here."
        data-testid="chapter-outline-text"
        @input="handleChapterInput"
        @focus="$emit('focus-area', 'chapter_outline')"
      />
      <footer class="outline-footer">
        <span class="save-status">{{ chapterSaveStatus }}</span>
        <button
          type="button"
          class="save-button"
          :disabled="!activeChapterId || chapterSaveStatus === 'saving'"
          @click="handleChapterSave"
        >
          Save Chapter Outline
        </button>
      </footer>
    </section>

    <AssetConflictModal
      :model-value="conflictVisible"
      description="The work outline was modified elsewhere. Resolve before clearing the local draft."
      :local-content="draftText"
      :server-content="serverContent"
      @cancel="assetStore.clearAssetConflict"
      @discard="handleDiscardLocal"
      @override="handleOverride"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import { useWritingAssetStore } from '@/stores/writingAsset'
import AssetConflictModal from './AssetConflictModal.vue'

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
const draftText = ref('')
const chapterDraftText = ref('')

const assetKey = 'work_outline:work'
const draft = computed(() => assetStore.assetDrafts[assetKey] || null)
const outline = computed(() => assetStore.workOutline || null)
const activeChapterId = computed(() => String(props.activeChapterId || ''))
const chapterAssetKey = computed(() => activeChapterId.value ? `chapter_outline:${activeChapterId.value}` : '')
const chapterDraft = computed(() => assetStore.assetDrafts[chapterAssetKey.value] || null)
const chapterOutline = computed(() => assetStore.chapterOutlines[activeChapterId.value] || null)
const isDirty = computed(() => assetStore.dirtyAssetKeys.includes(assetKey))
const chapterOutlineDirty = computed(() => Boolean(chapterAssetKey.value && assetStore.dirtyAssetKeys.includes(chapterAssetKey.value)))
const saveStatus = computed(() => assetStore.getAssetSaveStatus('work_outline', 'work'))
const chapterSaveStatus = computed(() => assetStore.getAssetSaveStatus('chapter_outline', activeChapterId.value))
const conflictVisible = computed(() => (
  assetStore.assetConflictPayload?.asset_type === 'work_outline'
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

const buildSavePayload = (overrides = {}) => ({
  content_text: draftText.value,
  content_tree_json: outline.value?.content_tree_json ?? [],
  expected_version: outline.value?.version ?? 1,
  ...overrides
})

const buildChapterSavePayload = (overrides = {}) => ({
  content_text: chapterDraftText.value,
  content_tree_json: chapterOutline.value?.content_tree_json ?? [],
  expected_version: chapterOutline.value?.version ?? 1,
  ...overrides
})

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
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleChapterSave = async () => {
  if (!activeChapterId.value) return
  if (!assetStore.assetDrafts[chapterAssetKey.value]) {
    assetStore.writeAssetDraft('chapter_outline', activeChapterId.value, buildChapterSavePayload())
  }
  try {
    await assetStore.saveChapterOutline(activeChapterId.value)
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleOverride = async () => {
  assetStore.writeAssetDraft('work_outline', 'work', buildSavePayload({ force_override: true }))
  try {
    await assetStore.saveWorkOutline()
    assetStore.clearAssetConflict()
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleDiscardLocal = async () => {
  assetStore.discardAssetDraft('work_outline', 'work')
  assetStore.clearAssetConflict()
  if (props.workId) {
    await assetStore.loadWorkOutline(props.workId)
  }
  syncFromStore()
}

const discardChapterLocal = async () => {
  if (!activeChapterId.value) return
  assetStore.discardAssetDraft('chapter_outline', activeChapterId.value)
  if (props.workId) {
    await assetStore.loadChapterOutline(activeChapterId.value)
  }
  syncChapterFromStore()
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
  saveFocusedDraft(area = 'work_outline') {
    return area === 'chapter_outline' ? handleChapterSave() : handleSave()
  },
  discardFocusedDraft(area = 'work_outline') {
    return area === 'chapter_outline' ? discardChapterLocal() : handleDiscardLocal()
  }
})
</script>

<style scoped>
.outline-panel {
  display: grid;
  gap: 14px;
}

.outline-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.outline-header h3 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.outline-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.dirty-indicator {
  align-self: start;
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

.outline-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chapter-outline-section {
  display: grid;
  gap: 14px;
  margin-top: 10px;
  border-top: 1px solid #e5e7eb;
  padding-top: 18px;
}

.chapter-outline-textarea {
  min-height: 220px;
}

.save-status {
  color: #6b7280;
  font-size: 13px;
}

.save-button {
  border: 0;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  padding: 10px 18px;
  font-weight: 700;
  cursor: pointer;
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
