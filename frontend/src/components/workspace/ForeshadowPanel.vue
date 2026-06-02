<template>
  <section class="foreshadow-panel" data-panel="foreshadow">
    <header class="panel-header">
      <div>
        <h3>伏笔</h3>
        <p>按状态筛选伏笔，编辑后需手动保存。</p>
      </div>
      <button type="button" class="create-button" @click="handleCreate">
        新建伏笔
      </button>
    </header>

    <section v-if="plotArcVisible" class="plot-arc-section">
      <header class="plot-arc-header">
        <h4>卷弧提示</h4>
        <span class="plot-arc-status">{{ plotArcStatusLabel }}</span>
      </header>
      <p v-if="volumeSummary.stage_goal" class="plot-arc-text">{{ volumeSummary.stage_goal }}</p>
      <ul v-if="volumeOpenLoops.length" class="plot-arc-list">
        <li v-for="loop in volumeOpenLoops" :key="loop">{{ loop }}</li>
      </ul>
    </section>

    <div class="status-tabs" role="tablist" aria-label="伏笔状态筛选">
      <button
        v-for="item in statusTabs"
        :key="item.value"
        type="button"
        class="status-tab"
        :class="{ active: item.value === activeStatus }"
        :data-status="item.value"
        @click="switchStatus(item.value)"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="panel-layout">
      <aside class="foreshadow-list">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="foreshadow-item"
          :class="{ active: item.id === selectedItemId && !isCreating }"
          :data-item-id="item.id"
          @click="selectItem(item.id)"
        >
          <span class="item-title">{{ item.title || '未命名伏笔' }}</span>
          <span class="item-meta">{{ item.status === 'resolved' ? '已回收' : '进行中' }}</span>
        </button>
        <div v-if="!items.length" class="empty-state">当前状态下还没有伏笔。</div>
      </aside>

      <div class="foreshadow-editor">
        <header class="editor-header">
          <div>
            <h4>{{ isCreating ? '新建伏笔' : '伏笔编辑' }}</h4>
            <p v-if="selectedItem">版本 {{ selectedItem.version }}</p>
          </div>
          <span v-if="isDirty" class="dirty-indicator">未保存</span>
        </header>

        <label class="field">
          <span>标题</span>
          <input
            v-model="draft.title"
            type="text"
            data-testid="foreshadow-title"
            @focus="emit('focus-area', 'foreshadow')"
            @input="handleDraftChange"
          />
        </label>

        <label class="field">
          <span>描述</span>
          <textarea
            v-model="draft.description"
            rows="8"
            data-testid="foreshadow-description"
            @focus="emit('focus-area', 'foreshadow')"
            @input="handleDraftChange"
          />
        </label>

        <label class="field">
          <span>状态</span>
          <select
            v-model="draft.status"
            data-testid="foreshadow-status"
            @focus="emit('focus-area', 'foreshadow')"
            @change="handleStatusChange"
          >
            <option value="open">进行中</option>
            <option value="resolved">已回收</option>
          </select>
        </label>

        <label class="field">
          <span>埋入章节</span>
          <select
            v-model="draft.introduced_chapter_id"
            data-testid="foreshadow-introduced"
            @focus="emit('focus-area', 'foreshadow')"
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

        <label class="field">
          <span>回收章节</span>
          <select
            v-model="draft.resolved_chapter_id"
            data-testid="foreshadow-resolved"
            :disabled="draft.status !== 'resolved'"
            @focus="emit('focus-area', 'foreshadow')"
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
              {{ isCreating ? '创建伏笔' : '保存伏笔' }}
            </button>
          </div>
        </footer>
      </div>
    </div>

    <AssetConflictModal
      :model-value="conflictVisible"
      description="当前伏笔已在其他位置被修改，请先处理冲突，再决定是否清除本地草稿。"
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

import { aiApi } from '@/api'
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
  },
  activeChapterId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['focus-area'])

const NEW_ITEM_ID = '__new__'
const statusTabs = [
  { value: 'open', label: '进行中' },
  { value: 'resolved', label: '已回收' }
]

const assetStore = useWritingAssetStore()
const saveStatusLabelMap = {
  idle: '待保存',
  saving: '保存中',
  synced: '已保存',
  error: '保存失败'
}
const activeStatus = ref('open')
const selectedItemId = ref('')
const isCreating = ref(false)
const draft = reactive({
  title: '',
  description: '',
  status: 'open',
  introduced_chapter_id: '',
  resolved_chapter_id: ''
})

const items = computed(() => [...assetStore.foreshadows])
const selectedItem = computed(() => (
  items.value.find((item) => item.id === selectedItemId.value) || null
))
const currentAssetId = computed(() => (isCreating.value ? NEW_ITEM_ID : selectedItemId.value))
const currentDraftKey = computed(() => (
  currentAssetId.value ? `foreshadow:${currentAssetId.value}` : ''
))
const currentDraft = computed(() => (
  currentDraftKey.value ? assetStore.assetDrafts[currentDraftKey.value] || null : null
))
const isDirty = computed(() => (
  currentDraftKey.value ? assetStore.dirtyAssetKeys.includes(currentDraftKey.value) : false
))
const saveStatus = computed(() => (
  isCreating.value
    ? assetStore.getAssetSaveStatus('foreshadow', NEW_ITEM_ID)
    : assetStore.getAssetSaveStatus('foreshadow', selectedItemId.value)
))
const saveStatusLabel = computed(() => saveStatusLabelMap[saveStatus.value] || saveStatusLabelMap.idle)
const canDelete = computed(() => isCreating.value || Boolean(selectedItem.value))
const conflictVisible = computed(() => assetStore.assetConflictPayload?.asset_type === 'foreshadow')
const conflictItemId = computed(() => String(assetStore.assetConflictPayload?.asset_id || ''))
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
const plotArcStatusMap = {
  ready: '可继续（ready）',
  degraded: '信息可能不足（degraded）',
  blocked: '无法继续（blocked）',
  pending: '待处理（pending）',
  unknown: '未知（unknown）'
}
const plotArcStatusLabel = computed(() => {
  const status = String(assetStore.contextPackReadiness?.status || 'unknown')
  return plotArcStatusMap[status] || status
})
const volumeSummary = computed(() => assetStore.plotArcSummary?.volume_arc || {})
const volumeOpenLoops = computed(() => {
  const items = volumeSummary.value?.stage_open_loops
  return Array.isArray(items) ? items.filter(Boolean) : []
})
const plotArcVisible = computed(() => Boolean(volumeSummary.value?.stage_goal || volumeOpenLoops.value.length))
const localConflictContent = computed(() => {
  const payload = assetStore.assetConflictPayload?.payload || {}
  return [
    `标题：${String(payload.title || '')}`,
    `状态：${String(payload.status || '')}`,
    `描述：${String(payload.description || '')}`,
    `埋入章节：${String(payload.introduced_chapter_id || '')}`,
    `回收章节：${String(payload.resolved_chapter_id || '')}`
  ].join('\n')
})
const serverConflictContent = computed(() => String(assetStore.assetConflictPayload?.server_content || ''))

const loadPlotArcSummary = async () => {
  if (!props.workId || !props.activeChapterId) return
  const payload = await aiApi.getContextPackReadiness(props.workId, props.activeChapterId)
  const readiness = payload?.data ?? payload ?? {}
  assetStore.contextPackReadiness = readiness
  assetStore.plotArcStatuses = readiness.plot_arc_statuses || {}
  assetStore.plotArcSummary = readiness.plot_arc_summary || {}
  assetStore.plotArcChapterId = String(props.activeChapterId || '')
}

const buildDraftPayload = (item = selectedItem.value) => ({
  title: String(draft.title || ''),
  description: String(draft.description || ''),
  status: draft.status === 'resolved' ? 'resolved' : 'open',
  introduced_chapter_id: draft.introduced_chapter_id ? String(draft.introduced_chapter_id) : null,
  resolved_chapter_id: draft.status === 'resolved' && draft.resolved_chapter_id
    ? String(draft.resolved_chapter_id)
    : null,
  expected_version: Number(item?.version || 1)
})

const syncDraftFromSelected = () => {
  if (isCreating.value) {
    const cached = assetStore.assetDrafts[`foreshadow:${NEW_ITEM_ID}`]?.payload || {}
    draft.title = String(cached.title || '')
    draft.description = String(cached.description || '')
    draft.status = String(cached.status || activeStatus.value || 'open')
    draft.introduced_chapter_id = String(cached.introduced_chapter_id || '')
    draft.resolved_chapter_id = String(cached.resolved_chapter_id || '')
    return
  }
  const payload = currentDraft.value?.payload || selectedItem.value || {}
  draft.title = String(payload.title || '')
  draft.description = String(payload.description || '')
  draft.status = String(payload.status || activeStatus.value || 'open')
  draft.introduced_chapter_id = String(payload.introduced_chapter_id || '')
  draft.resolved_chapter_id = String(payload.resolved_chapter_id || '')
}

const ensureSelection = () => {
  if (isCreating.value) return
  if (selectedItem.value) return
  selectedItemId.value = String(items.value[0]?.id || '')
}

const selectItem = (itemId) => {
  isCreating.value = false
  selectedItemId.value = String(itemId || '')
  syncDraftFromSelected()
}

const handleCreate = () => {
  isCreating.value = true
  selectedItemId.value = ''
  draft.title = ''
  draft.description = ''
  draft.status = activeStatus.value
  draft.introduced_chapter_id = ''
  draft.resolved_chapter_id = ''
  emit('focus-area', 'foreshadow')
}

const handleDraftChange = () => {
  emit('focus-area', 'foreshadow')
  if (draft.status !== 'resolved') {
    draft.resolved_chapter_id = ''
  }
  if (isCreating.value) {
    assetStore.writeAssetDraft('foreshadow', NEW_ITEM_ID, {
      title: String(draft.title || ''),
      description: String(draft.description || ''),
      status: draft.status === 'resolved' ? 'resolved' : 'open',
      introduced_chapter_id: draft.introduced_chapter_id ? String(draft.introduced_chapter_id) : null,
      resolved_chapter_id: draft.status === 'resolved' && draft.resolved_chapter_id
        ? String(draft.resolved_chapter_id)
        : null
    })
    return
  }
  if (!selectedItem.value) return
  assetStore.writeAssetDraft('foreshadow', selectedItem.value.id, buildDraftPayload())
}

const handleStatusChange = () => {
  if (draft.status !== 'resolved') {
    draft.resolved_chapter_id = ''
  }
  handleDraftChange()
}

const saveCurrentDraft = async (forceOverride = false) => {
  if (isCreating.value) {
    const created = await assetStore.createForeshadow({
      title: String(draft.title || ''),
      description: String(draft.description || ''),
      status: draft.status === 'resolved' ? 'resolved' : 'open',
      introduced_chapter_id: draft.introduced_chapter_id ? String(draft.introduced_chapter_id) : null,
      resolved_chapter_id: draft.status === 'resolved' && draft.resolved_chapter_id
        ? String(draft.resolved_chapter_id)
        : null
    })
    assetStore.discardAssetDraft('foreshadow', NEW_ITEM_ID)
    isCreating.value = false
    selectedItemId.value = String(created?.id || '')
    activeStatus.value = String(created?.status || activeStatus.value)
    syncDraftFromSelected()
    return created
  }

  if (!selectedItem.value) return null
  if (!currentDraft.value) {
    assetStore.writeAssetDraft('foreshadow', selectedItem.value.id, buildDraftPayload())
  } else if (forceOverride) {
    assetStore.writeAssetDraft('foreshadow', selectedItem.value.id, {
      ...currentDraft.value.payload,
      force_override: true
    })
  }
  const saved = await assetStore.updateForeshadow(selectedItem.value.id)
  if (saved?.status && saved.status !== activeStatus.value) {
    await assetStore.loadForeshadows(props.workId, activeStatus.value)
    ensureSelection()
  }
  return saved
}

const discardCurrentDraft = async () => {
  if (isCreating.value) {
    assetStore.discardAssetDraft('foreshadow', NEW_ITEM_ID)
    isCreating.value = false
    ensureSelection()
    syncDraftFromSelected()
    return
  }
  if (!selectedItem.value) return
  assetStore.discardAssetDraft('foreshadow', selectedItem.value.id)
  await assetStore.loadForeshadows(props.workId, activeStatus.value)
  ensureSelection()
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
  if (!selectedItem.value) return
  const currentId = selectedItem.value.id
  const currentIndex = items.value.findIndex((item) => item.id === currentId)
  await assetStore.deleteForeshadow(currentId)
  const nextItem = items.value[currentIndex] || items.value[currentIndex - 1] || null
  selectedItemId.value = String(nextItem?.id || '')
  syncDraftFromSelected()
}

const switchStatus = async (status) => {
  const nextStatus = status === 'resolved' ? 'resolved' : 'open'
  activeStatus.value = nextStatus
  isCreating.value = false
  selectedItemId.value = ''
  await assetStore.loadForeshadows(props.workId, nextStatus)
  ensureSelection()
  syncDraftFromSelected()
}

const handleOverrideConflict = async () => {
  if (conflictItemId.value) {
    const payload = assetStore.assetDrafts[`foreshadow:${conflictItemId.value}`]?.payload || buildDraftPayload()
    assetStore.writeAssetDraft('foreshadow', conflictItemId.value, {
      ...payload,
      force_override: true
    })
  }
  try {
    await assetStore.updateForeshadow(conflictItemId.value)
    assetStore.clearAssetConflict()
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleDiscardConflict = async () => {
  if (conflictItemId.value) {
    assetStore.discardAssetDraft('foreshadow', conflictItemId.value)
  }
  assetStore.clearAssetConflict()
  await assetStore.loadForeshadows(props.workId, activeStatus.value)
  ensureSelection()
  syncDraftFromSelected()
}

onMounted(async () => {
  if (props.workId) {
    assetStore.setWorkContext(props.workId)
    await assetStore.loadForeshadows(props.workId, activeStatus.value)
  }
  await loadPlotArcSummary()
  ensureSelection()
  syncDraftFromSelected()
})

watch(
  () => props.workId,
  async (nextWorkId, previousWorkId) => {
    if (!nextWorkId || nextWorkId === previousWorkId) return
    assetStore.setWorkContext(nextWorkId)
    await assetStore.loadForeshadows(nextWorkId, activeStatus.value)
    isCreating.value = false
    ensureSelection()
    syncDraftFromSelected()
  }
)

watch(
  () => props.activeChapterId,
  async (nextChapterId, previousChapterId) => {
    if (!nextChapterId || nextChapterId === previousChapterId) return
    await loadPlotArcSummary()
  }
)

watch(
  () => [items.value.map((item) => `${item.id}:${item.version}`).join('|'), currentDraft.value?.timestamp, isCreating.value, activeStatus.value],
  () => {
    ensureSelection()
    syncDraftFromSelected()
  }
)

defineExpose({
  saveFocusedDraft: saveCurrentDraft,
  discardFocusedDraft: discardCurrentDraft
})
</script>

<style scoped>
.foreshadow-panel {
  --panel-surface: var(--studio-card-bg, var(--ink-surface-1));
  --panel-surface-soft: var(--studio-bg-focus, var(--ink-surface-2));
  --panel-border: var(--studio-border, var(--ink-border));
  --panel-border-strong: var(--ink-border-strong);
  --panel-title: var(--studio-title, var(--ink-text-primary));
  --panel-text: var(--studio-text, var(--ink-text-secondary));
  --panel-muted: var(--studio-muted, var(--ink-text-muted));
  --panel-input-bg: var(--studio-input-bg, var(--ink-surface-1));
  --panel-button-bg: var(--studio-button-bg, var(--ink-surface-2));
  display: grid;
  gap: 14px;
}

.plot-arc-section {
  display: grid;
  gap: 8px;
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  background: var(--panel-surface-soft);
  padding: 12px;
}

.plot-arc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.plot-arc-header h4 {
  margin: 0;
  color: var(--panel-title);
}

.plot-arc-status {
  border-radius: 999px;
  background: var(--ink-warning-bg);
  color: var(--ink-warning-text);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
}

.plot-arc-text,
.plot-arc-list {
  margin: 0;
  color: var(--panel-text);
  font-size: 13px;
  line-height: 1.6;
}

.plot-arc-list {
  padding-left: 18px;
}

.panel-header,
.editor-header,
.editor-footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-header h3,
.editor-header h4 {
  margin: 0;
  color: var(--panel-title);
}

.panel-header p,
.editor-header p,
.save-status,
.empty-state {
  margin: 6px 0 0;
  color: var(--panel-muted);
  font-size: 13px;
  line-height: 1.6;
}

.status-tabs {
  display: flex;
  gap: 8px;
}

.status-tab,
.create-button,
.save-button,
.ghost-button {
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
}

.status-tab,
.ghost-button {
  background: var(--panel-button-bg);
  color: var(--panel-title);
  border: 1px solid var(--panel-border);
}

.status-tab.active {
  background: var(--ink-accent-soft);
  color: var(--ink-accent);
}

.create-button,
.save-button {
  background: var(--panel-title);
  color: var(--panel-surface);
}

.panel-layout {
  display: grid;
  gap: 16px;
}

.foreshadow-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 8px;
}

.foreshadow-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  background: var(--panel-surface);
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}

.item-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.foreshadow-item.active {
  border-color: var(--ink-accent);
  background: var(--ink-accent-soft);
}

.item-title {
  color: var(--panel-title);
  font-size: 14px;
  font-weight: 600;
}

.item-meta {
  color: var(--panel-muted);
  font-size: 12px;
}

.foreshadow-editor {
  display: grid;
  gap: 14px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  color: var(--panel-text);
  font-size: 13px;
  font-weight: 600;
}

.field input,
.field textarea,
.field select {
  width: 100%;
  border: 1px solid var(--panel-border-strong);
  border-radius: 14px;
  padding: 12px 14px;
  background: var(--panel-input-bg);
  color: var(--panel-title);
  font: inherit;
}

.field select,
.field option {
  background: var(--panel-input-bg);
  color: var(--panel-title);
}

.field input::placeholder,
.field textarea::placeholder {
  color: var(--panel-muted);
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
  background: var(--ink-warning-bg);
  color: var(--ink-warning-text);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 900px) {
  .panel-layout {
    gap: 14px;
  }

  .foreshadow-list {
    grid-template-columns: 1fr;
  }
}
</style>

