<template>
  <section class="character-panel" data-panel="character">
    <header class="panel-header">
      <div>
        <h3>人物</h3>
        <p>支持人物姓名、别名和描述维护，编辑后需手动保存。</p>
      </div>
      <button type="button" class="create-button" @click="handleCreate">
        新建人物
      </button>
    </header>

    <label class="search-field">
      <span>搜索</span>
      <input
        v-model="searchKeyword"
        type="text"
        placeholder="按姓名或别名搜索"
        data-testid="character-search"
        @input="handleSearch"
      />
    </label>

    <div class="panel-layout">
      <aside class="character-list">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="character-item"
          :class="{ active: item.id === selectedItemId && !isCreating }"
          :data-item-id="item.id"
          @click="selectItem(item.id)"
        >
          <span class="item-title">{{ item.name || '未命名人物' }}</span>
          <span class="item-meta">{{ formatAliases(item.aliases) }}</span>
        </button>
        <div v-if="!items.length" class="empty-state">当前搜索没有匹配到人物。</div>
      </aside>

      <div class="character-editor">
        <header class="editor-header">
          <div>
            <h4>{{ isCreating ? '新建人物' : '人物编辑' }}</h4>
            <p v-if="selectedItem">版本 {{ selectedItem.version }}</p>
          </div>
          <span v-if="isDirty" class="dirty-indicator">未保存</span>
        </header>

        <p v-if="showDuplicateWarning" class="duplicate-warning">
          检测到重名人物，仍可继续保存。
        </p>

        <label class="field">
          <span>姓名</span>
          <input
            v-model="draft.name"
            type="text"
            data-testid="character-name"
            @focus="emit('focus-area', 'character')"
            @input="handleDraftChange"
          />
        </label>

        <label class="field">
          <span>别名</span>
          <input
            v-model="aliasesInput"
            type="text"
            placeholder="多个别名请用逗号分隔"
            data-testid="character-aliases"
            @focus="emit('focus-area', 'character')"
            @input="handleAliasesInput"
          />
        </label>

        <label class="field">
          <span>描述</span>
          <textarea
            v-model="draft.description"
            rows="8"
            data-testid="character-description"
            @focus="emit('focus-area', 'character')"
            @input="handleDraftChange"
          />
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
              {{ isCreating ? '创建人物' : '保存人物' }}
            </button>
          </div>
        </footer>
      </div>
    </div>

    <AssetConflictModal
      :model-value="conflictVisible"
      description="当前人物已在其他位置被修改，请先处理冲突，再决定是否清除本地草稿。"
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
  }
})

const emit = defineEmits(['focus-area'])

const NEW_ITEM_ID = '__new__'
const assetStore = useWritingAssetStore()
const saveStatusLabelMap = {
  idle: '待保存',
  saving: '保存中',
  synced: '已保存',
  error: '保存失败'
}
const searchKeyword = ref('')
const selectedItemId = ref('')
const isCreating = ref(false)
const aliasesInput = ref('')
const draft = reactive({
  name: '',
  description: '',
  aliases: []
})

const items = computed(() => [...assetStore.characters])
const selectedItem = computed(() => (
  items.value.find((item) => item.id === selectedItemId.value) || null
))
const currentAssetId = computed(() => (isCreating.value ? NEW_ITEM_ID : selectedItemId.value))
const currentDraftKey = computed(() => (
  currentAssetId.value ? `character:${currentAssetId.value}` : ''
))
const currentDraft = computed(() => (
  currentDraftKey.value ? assetStore.assetDrafts[currentDraftKey.value] || null : null
))
const isDirty = computed(() => (
  currentDraftKey.value ? assetStore.dirtyAssetKeys.includes(currentDraftKey.value) : false
))
const saveStatus = computed(() => (
  isCreating.value
    ? assetStore.getAssetSaveStatus('character', NEW_ITEM_ID)
    : assetStore.getAssetSaveStatus('character', selectedItemId.value)
))
const saveStatusLabel = computed(() => saveStatusLabelMap[saveStatus.value] || saveStatusLabelMap.idle)
const canDelete = computed(() => isCreating.value || Boolean(selectedItem.value))
const conflictVisible = computed(() => assetStore.assetConflictPayload?.asset_type === 'character')
const conflictItemId = computed(() => String(assetStore.assetConflictPayload?.asset_id || ''))
const normalizedDraftName = computed(() => String(draft.name || '').trim().toLowerCase())
const showDuplicateWarning = computed(() => {
  if (!normalizedDraftName.value) return false
  return items.value.some((item) => {
    if (!isCreating.value && item.id === selectedItemId.value) return false
    return String(item.name || '').trim().toLowerCase() === normalizedDraftName.value
  })
})
const localConflictContent = computed(() => {
  const payload = assetStore.assetConflictPayload?.payload || {}
  return [
    `姓名：${String(payload.name || '')}`,
    `别名：${Array.isArray(payload.aliases) ? payload.aliases.join(', ') : ''}`,
    `描述：${String(payload.description || '')}`
  ].join('\n')
})
const serverConflictContent = computed(() => String(assetStore.assetConflictPayload?.server_content || ''))

const normalizeAliases = (value) => {
  const parts = String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  const deduped = []
  const seen = new Set()
  for (const item of parts) {
    const key = item.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(item)
  }
  return deduped
}

const formatAliases = (aliases) => {
  const items = Array.isArray(aliases) ? aliases.filter(Boolean) : []
  return items.length ? items.join(', ') : '暂无别名'
}

const buildDraftPayload = (item = selectedItem.value) => ({
  name: String(draft.name || '').trim(),
  description: String(draft.description || ''),
  aliases: [...draft.aliases],
  expected_version: Number(item?.version || 1)
})

const syncDraftFromSelected = () => {
  if (isCreating.value) {
    const cached = assetStore.assetDrafts[`character:${NEW_ITEM_ID}`]?.payload || {}
    draft.name = String(cached.name || '')
    draft.description = String(cached.description || '')
    draft.aliases = Array.isArray(cached.aliases) ? [...cached.aliases] : []
    aliasesInput.value = draft.aliases.join(', ')
    return
  }
  const payload = currentDraft.value?.payload || selectedItem.value || {}
  draft.name = String(payload.name || '')
  draft.description = String(payload.description || '')
  draft.aliases = Array.isArray(payload.aliases) ? [...payload.aliases] : []
  aliasesInput.value = draft.aliases.join(', ')
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
  draft.name = ''
  draft.description = ''
  draft.aliases = []
  aliasesInput.value = ''
  emit('focus-area', 'character')
}

const handleDraftChange = () => {
  emit('focus-area', 'character')
  if (isCreating.value) {
    assetStore.writeAssetDraft('character', NEW_ITEM_ID, {
      name: String(draft.name || '').trim(),
      description: String(draft.description || ''),
      aliases: [...draft.aliases]
    })
    return
  }
  if (!selectedItem.value) return
  assetStore.writeAssetDraft('character', selectedItem.value.id, buildDraftPayload())
}

const handleAliasesInput = (event) => {
  aliasesInput.value = String(event?.target?.value || '')
  draft.aliases = normalizeAliases(aliasesInput.value)
  handleDraftChange()
}

const handleSearch = async () => {
  await assetStore.loadCharacters(props.workId, searchKeyword.value)
  if (!items.value.some((item) => item.id === selectedItemId.value)) {
    selectedItemId.value = ''
  }
  ensureSelection()
  syncDraftFromSelected()
}

const saveCurrentDraft = async (forceOverride = false) => {
  if (isCreating.value) {
    const created = await assetStore.createCharacter({
      name: String(draft.name || '').trim(),
      description: String(draft.description || ''),
      aliases: [...draft.aliases]
    })
    assetStore.discardAssetDraft('character', NEW_ITEM_ID)
    isCreating.value = false
    selectedItemId.value = String(created?.id || '')
    syncDraftFromSelected()
    return created
  }

  if (!selectedItem.value) return null
  if (!currentDraft.value) {
    assetStore.writeAssetDraft('character', selectedItem.value.id, buildDraftPayload())
  } else if (forceOverride) {
    assetStore.writeAssetDraft('character', selectedItem.value.id, {
      ...currentDraft.value.payload,
      force_override: true
    })
  }
  return assetStore.updateCharacter(selectedItem.value.id)
}

const discardCurrentDraft = async () => {
  if (isCreating.value) {
    assetStore.discardAssetDraft('character', NEW_ITEM_ID)
    isCreating.value = false
    ensureSelection()
    syncDraftFromSelected()
    return
  }
  if (!selectedItem.value) return
  assetStore.discardAssetDraft('character', selectedItem.value.id)
  await assetStore.loadCharacters(props.workId, searchKeyword.value)
  ensureSelection()
  syncDraftFromSelected()
}

const handleSave = async () => {
  if (!String(draft.name || '').trim()) return
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
  await assetStore.deleteCharacter(currentId)
  const nextItem = items.value[currentIndex] || items.value[currentIndex - 1] || null
  selectedItemId.value = String(nextItem?.id || '')
  syncDraftFromSelected()
}

const handleOverrideConflict = async () => {
  if (conflictItemId.value) {
    const payload = assetStore.assetDrafts[`character:${conflictItemId.value}`]?.payload || buildDraftPayload()
    assetStore.writeAssetDraft('character', conflictItemId.value, {
      ...payload,
      force_override: true
    })
  }
  try {
    await assetStore.updateCharacter(conflictItemId.value)
    assetStore.clearAssetConflict()
  } catch (error) {
    if (!assetStore.assetConflictPayload) {
      throw error
    }
  }
}

const handleDiscardConflict = async () => {
  if (conflictItemId.value) {
    assetStore.discardAssetDraft('character', conflictItemId.value)
  }
  assetStore.clearAssetConflict()
  await assetStore.loadCharacters(props.workId, searchKeyword.value)
  ensureSelection()
  syncDraftFromSelected()
}

onMounted(async () => {
  if (props.workId) {
    assetStore.setWorkContext(props.workId)
    await assetStore.loadCharacters(props.workId, searchKeyword.value)
  }
  ensureSelection()
  syncDraftFromSelected()
})

watch(
  () => props.workId,
  async (nextWorkId, previousWorkId) => {
    if (!nextWorkId || nextWorkId === previousWorkId) return
    assetStore.setWorkContext(nextWorkId)
    await assetStore.loadCharacters(nextWorkId, searchKeyword.value)
    isCreating.value = false
    ensureSelection()
    syncDraftFromSelected()
  }
)

watch(
  () => [items.value.map((item) => `${item.id}:${item.version}`).join('|'), currentDraft.value?.timestamp, isCreating.value],
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
.character-panel {
  display: grid;
  gap: 14px;
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
  color: #111827;
}

.panel-header p,
.editor-header p,
.save-status,
.empty-state,
.duplicate-warning {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.duplicate-warning {
  border-radius: 12px;
  background: #fef3c7;
  color: #92400e;
  padding: 10px 12px;
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

.search-field,
.field {
  display: grid;
  gap: 8px;
}

.search-field span,
.field span {
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}

.search-field input,
.field input,
.field textarea {
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

.panel-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 16px;
}

.character-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.character-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}

.character-item.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.item-title {
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.item-meta {
  color: #6b7280;
  font-size: 12px;
}

.character-editor {
  display: grid;
  gap: 14px;
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
  .panel-layout {
    grid-template-columns: 1fr;
  }
}
</style>
