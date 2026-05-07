<template>
  <section class="timeline-panel" data-panel="timeline">
    <header class="timeline-header">
      <div>
        <h3>时间线</h3>
        <p>按顺序维护故事事件，编辑后需手动保存。</p>
      </div>
      <button type="button" class="create-button" @click="handleCreate">
        新建事件
      </button>
    </header>

    <div class="timeline-layout">
      <aside class="timeline-list">
        <button
          v-for="item in events"
          :key="item.id"
          type="button"
          class="timeline-item"
          :class="{ active: item.id === selectedEventId && !isCreating }"
          :data-event-id="item.id"
          @click="selectEvent(item.id)"
        >
          <span class="timeline-item-title">{{ item.title || `事件 ${item.order_index}` }}</span>
          <span class="timeline-item-meta">#{{ item.order_index }}</span>
        </button>
        <div v-if="!events.length" class="timeline-empty">当前还没有时间线事件。</div>
      </aside>

      <div class="timeline-editor">
        <header class="editor-header">
          <div>
            <h4>{{ isCreating ? '新建事件' : '事件编辑' }}</h4>
            <p v-if="selectedEvent">
              顺序 {{ selectedEvent.order_index }} · 版本 {{ selectedEvent.version }}
            </p>
          </div>
          <span v-if="isDirty || reorderDirty" class="dirty-indicator">未保存</span>
        </header>

        <div v-if="selectedEvent && !isCreating" class="reorder-actions">
          <button
            type="button"
            class="ghost-button"
            data-testid="timeline-move-up"
            :disabled="!canMoveUp"
            @click="handleMove('up')"
          >
            上移
          </button>
          <button
            type="button"
            class="ghost-button"
            data-testid="timeline-move-down"
            :disabled="!canMoveDown"
            @click="handleMove('down')"
          >
            下移
          </button>
          <button
            v-if="reorderDirty"
            type="button"
            class="save-button"
            data-testid="timeline-save-order"
            :disabled="reorderSaveStatus === 'saving'"
            @click="handleSaveReorder"
          >
            保存顺序
          </button>
        </div>

        <label class="field">
          <span>标题</span>
          <input
            v-model="draft.title"
            type="text"
            data-testid="timeline-title"
            @focus="emit('focus-area', 'timeline')"
            @input="handleDraftChange"
          />
        </label>

        <label class="field">
          <span>描述</span>
          <textarea
            v-model="draft.description"
            rows="8"
            data-testid="timeline-description"
            @focus="emit('focus-area', 'timeline')"
            @input="handleDraftChange"
          />
        </label>

        <label class="field">
          <span>关联章节</span>
          <select
            v-model="draft.chapter_id"
            data-testid="timeline-chapter"
            @focus="emit('focus-area', 'timeline')"
            @change="handleDraftChange"
          >
            <option value="">不关联章节</option>
            <option
              v-for="chapter in chapterOptions"
              :key="chapter.id"
              :value="chapter.id"
            >
              {{ chapter.label }}
            </option>
          </select>
        </label>

        <footer class="editor-footer">
          <span class="save-status">{{ saveStatusLabel }}</span>
          <div class="editor-actions">
            <button
              type="button"
              class="ghost-button"
              :disabled="!canDelete"
              @click="handleDelete"
            >
              删除
            </button>
            <button
              type="button"
              class="save-button"
              :disabled="saveStatus === 'saving'"
              @click="handleSave"
            >
              {{ isCreating ? '创建事件' : '保存事件' }}
            </button>
          </div>
        </footer>
      </div>
    </div>

    <AssetConflictModal
      :model-value="conflictVisible"
      description="当前时间线事件已在其他位置被修改，请先处理冲突，再决定是否清除本地草稿。"
      :local-content="localConflictContent"
      :server-content="serverConflictContent"
      @cancel="assetStore.clearAssetConflict"
      @discard="handleDiscardConflict"
      @override="handleOverrideConflict"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { useWritingAssetStore } from '@/stores/writingAsset'
import AssetConflictModal from './AssetConflictModal.vue'

const props = defineProps({
  workId: {
    type: String,
    default: ''
  },
  chapters: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['focus-area'])

const NEW_EVENT_ID = '__new__'
const assetStore = useWritingAssetStore()
const saveStatusLabelMap = {
  idle: '待保存',
  saving: '保存中',
  synced: '已保存',
  error: '保存失败'
}
const selectedEventId = ref('')
const isCreating = ref(false)
const draft = reactive({
  title: '',
  description: '',
  chapter_id: ''
})

const events = computed(() => [...assetStore.timeline].sort((left, right) => (
  Number(left?.order_index || 0) - Number(right?.order_index || 0)
)))
const selectedEvent = computed(() => (
  events.value.find((item) => item.id === selectedEventId.value) || null
))
const currentAssetId = computed(() => (isCreating.value ? NEW_EVENT_ID : selectedEventId.value))
const currentDraftKey = computed(() => (
  currentAssetId.value ? `timeline:${currentAssetId.value}` : ''
))
const currentDraft = computed(() => (
  currentDraftKey.value ? assetStore.assetDrafts[currentDraftKey.value] || null : null
))
const isDirty = computed(() => (
  currentDraftKey.value ? assetStore.dirtyAssetKeys.includes(currentDraftKey.value) : false
))
const saveStatus = computed(() => (
  isCreating.value
    ? assetStore.getAssetSaveStatus('timeline', NEW_EVENT_ID)
    : assetStore.getAssetSaveStatus('timeline', selectedEventId.value)
))
const saveStatusLabel = computed(() => saveStatusLabelMap[saveStatus.value] || saveStatusLabelMap.idle)
const conflictVisible = computed(() => assetStore.assetConflictPayload?.asset_type === 'timeline')
const conflictEventId = computed(() => String(assetStore.assetConflictPayload?.asset_id || ''))
const reorderDraftKey = 'timeline:__reorder__'
const reorderDirty = computed(() => assetStore.dirtyAssetKeys.includes(reorderDraftKey))
const reorderSaveStatus = computed(() => assetStore.getAssetSaveStatus('timeline', '__reorder__'))
const chapterOptions = computed(() => (
  (props.chapters || []).map((chapter, index) => {
    const orderIndex = Number(chapter?.order_index) || index + 1
    const title = String(chapter?.title || '').trim()
    return {
      id: String(chapter?.id || ''),
      label: title ? `第${orderIndex}章 ${title}` : `第${orderIndex}章`
    }
  }).filter((chapter) => chapter.id)
))
const localConflictContent = computed(() => {
  const payload = assetStore.assetConflictPayload?.payload || {}
  return [
    `标题：${String(payload.title || '')}`,
    `描述：${String(payload.description || '')}`,
    `章节：${String(payload.chapter_id || '')}`
  ].join('\n')
})
const serverConflictContent = computed(() => String(assetStore.assetConflictPayload?.server_content || ''))

const buildDraftPayload = (event = selectedEvent.value) => ({
  title: String(draft.title || ''),
  description: String(draft.description || ''),
  chapter_id: draft.chapter_id ? String(draft.chapter_id) : null,
  expected_version: Number(event?.version || 1)
})

const syncDraftFromSelected = () => {
  if (isCreating.value) {
    const cached = assetStore.assetDrafts[`timeline:${NEW_EVENT_ID}`]?.payload || {}
    draft.title = String(cached.title || '')
    draft.description = String(cached.description || '')
    draft.chapter_id = String(cached.chapter_id || '')
    return
  }
  const payload = currentDraft.value?.payload || selectedEvent.value || {}
  draft.title = String(payload.title || '')
  draft.description = String(payload.description || '')
  draft.chapter_id = String(payload.chapter_id || '')
}

const ensureSelection = () => {
  if (isCreating.value) return
  if (selectedEvent.value) return
  selectedEventId.value = String(events.value[0]?.id || '')
}

const selectEvent = (eventId) => {
  isCreating.value = false
  selectedEventId.value = String(eventId || '')
  syncDraftFromSelected()
}

const handleCreate = () => {
  isCreating.value = true
  selectedEventId.value = ''
  emit('focus-area', 'timeline')
  syncDraftFromSelected()
}

const handleDraftChange = () => {
  emit('focus-area', 'timeline')
  if (isCreating.value) {
    assetStore.writeAssetDraft('timeline', NEW_EVENT_ID, {
      title: String(draft.title || ''),
      description: String(draft.description || ''),
      chapter_id: draft.chapter_id ? String(draft.chapter_id) : null
    })
    return
  }
  if (!selectedEvent.value) return
  assetStore.writeAssetDraft('timeline', selectedEvent.value.id, buildDraftPayload())
}

const saveCurrentDraft = async (forceOverride = false) => {
  if (isCreating.value) {
    const payload = {
      title: String(draft.title || ''),
      description: String(draft.description || ''),
      chapter_id: draft.chapter_id ? String(draft.chapter_id) : null
    }
    const created = await assetStore.createTimelineEvent(payload)
    assetStore.discardAssetDraft('timeline', NEW_EVENT_ID)
    isCreating.value = false
    selectedEventId.value = String(created?.id || '')
    syncDraftFromSelected()
    return created
  }

  if (!selectedEvent.value) return null
  if (!currentDraft.value) {
    assetStore.writeAssetDraft('timeline', selectedEvent.value.id, buildDraftPayload())
  } else if (forceOverride) {
    assetStore.writeAssetDraft('timeline', selectedEvent.value.id, {
      ...currentDraft.value.payload,
      force_override: true
    })
  }
  return assetStore.updateTimelineEvent(selectedEvent.value.id)
}

const discardCurrentDraft = async () => {
  if (isCreating.value) {
    assetStore.discardAssetDraft('timeline', NEW_EVENT_ID)
    isCreating.value = false
    ensureSelection()
    syncDraftFromSelected()
    return
  }
  if (!selectedEvent.value) return
  assetStore.discardAssetDraft('timeline', selectedEvent.value.id)
  await assetStore.loadTimeline(props.workId)
  syncDraftFromSelected()
}

const handleSave = async () => {
  try {
    await saveCurrentDraft(false)
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleDelete = async () => {
  if (isCreating.value) {
    await discardCurrentDraft()
    return
  }
  if (!selectedEvent.value) return
  const currentId = selectedEvent.value.id
  const currentIndex = events.value.findIndex((item) => item.id === currentId)
  await assetStore.deleteTimelineEvent(currentId)
  const nextItem = events.value[currentIndex] || events.value[currentIndex - 1] || null
  selectedEventId.value = String(nextItem?.id || '')
  syncDraftFromSelected()
}

const handleMove = (direction) => {
  emit('focus-area', 'timeline_reorder')
  if (!selectedEvent.value) return
  const currentIndex = selectedIndex.value
  const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= events.value.length) return
  const nextItems = [...events.value]
  const [current] = nextItems.splice(currentIndex, 1)
  nextItems.splice(targetIndex, 0, current)
  assetStore.stageTimelineReorder(nextItems)
}

const handleSaveReorder = async () => {
  emit('focus-area', 'timeline_reorder')
  await assetStore.reorderTimelineEvents()
}

const handleOverrideConflict = async () => {
  if (conflictEventId.value) {
    const payload = assetStore.assetDrafts[`timeline:${conflictEventId.value}`]?.payload || buildDraftPayload()
    assetStore.writeAssetDraft('timeline', conflictEventId.value, {
      ...payload,
      force_override: true
    })
  }
  try {
    await assetStore.updateTimelineEvent(conflictEventId.value)
    assetStore.clearAssetConflict()
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleDiscardConflict = async () => {
  if (conflictEventId.value) {
    assetStore.discardAssetDraft('timeline', conflictEventId.value)
  }
  assetStore.clearAssetConflict()
  await assetStore.loadTimeline(props.workId)
  ensureSelection()
  syncDraftFromSelected()
}

const canDelete = computed(() => isCreating.value || Boolean(selectedEvent.value))
const selectedIndex = computed(() => events.value.findIndex((item) => item.id === selectedEventId.value))
const canMoveUp = computed(() => selectedIndex.value > 0)
const canMoveDown = computed(() => selectedIndex.value >= 0 && selectedIndex.value < events.value.length - 1)

onMounted(async () => {
  if (props.workId) {
    assetStore.setWorkContext(props.workId)
    if (!assetStore.timeline.length) {
      await assetStore.loadTimeline(props.workId)
    }
  }
  ensureSelection()
  syncDraftFromSelected()
})

watch(
  () => props.workId,
  async (nextWorkId, previousWorkId) => {
    if (!nextWorkId || nextWorkId === previousWorkId) return
    assetStore.setWorkContext(nextWorkId)
    await assetStore.loadTimeline(nextWorkId)
    isCreating.value = false
    ensureSelection()
    syncDraftFromSelected()
  }
)

watch(
  () => [events.value.map((item) => `${item.id}:${item.version}`).join('|'), currentDraft.value?.timestamp, isCreating.value],
  () => {
    ensureSelection()
    syncDraftFromSelected()
  }
)

defineExpose({
  saveFocusedDraft(mode = 'event') {
    return mode === 'reorder' ? handleSaveReorder() : saveCurrentDraft()
  },
  discardFocusedDraft: discardCurrentDraft
})
</script>

<style scoped>
.timeline-panel {
  display: grid;
  gap: 14px;
}

.timeline-header,
.editor-header,
.editor-footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.timeline-header h3,
.editor-header h4 {
  margin: 0;
  color: #111827;
}

.timeline-header p,
.editor-header p,
.save-status,
.timeline-empty {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.create-button,
.save-button,
.ghost-button {
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
}

.create-button,
.save-button {
  background: #111827;
  color: #ffffff;
}

.ghost-button {
  background: #f3f4f6;
  color: #111827;
}

.timeline-layout {
  display: grid;
  gap: 16px;
}

.timeline-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 8px;
}

.timeline-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}

.timeline-item-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-item.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.timeline-item-title {
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.timeline-item-meta {
  color: #6b7280;
  font-size: 12px;
}

.timeline-editor {
  display: grid;
  gap: 14px;
}

.reorder-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}

.field input,
.field textarea,
.field select {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 14px;
  padding: 12px 14px;
  color: #111827;
  font: inherit;
}

.field textarea {
  resize: vertical;
}

.editor-actions {
  display: flex;
  gap: 8px;
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

@media (max-width: 900px) {
  .timeline-layout {
    gap: 14px;
  }

  .timeline-list {
    grid-template-columns: 1fr;
  }
}
</style>
