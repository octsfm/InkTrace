<template>
  <div class="chapter-sidebar">
    <div class="sidebar-header">
      <div>
        <h2>章节列表</h2>
        <p>{{ chapters.length }} 章</p>
      </div>
      <button type="button" class="add-button" @click="handleCreate">+ 新章</button>
    </div>

    <div class="sidebar-tools">
      <input
        v-model="searchQuery"
        class="sidebar-tool-input"
        type="text"
        placeholder="搜索章节"
      />
      <form class="jump-form" @submit.prevent="submitJump">
        <input
          v-model="jumpOrderInput"
          class="sidebar-tool-input"
          type="text"
          inputmode="numeric"
          placeholder="跳转第 N 章"
        />
        <button type="submit" class="jump-button">跳转</button>
      </form>
    </div>

    <div v-if="loading" class="sidebar-state">正在加载章节...</div>
    <div v-else-if="!chapters.length" class="sidebar-state">当前还没有章节。</div>
    <div v-else-if="filteredChapters.length === 0" class="sidebar-state">没有找到匹配章节。</div>
    <div v-else class="chapter-list">
      <div
        v-for="chapter in filteredChapters"
        :key="chapter.id"
        :data-chapter-id="chapter.id"
        class="chapter-item"
        :class="{
          active: chapter.id === activeChapterId,
          editing: chapter.id === editingChapterId,
          dragging: chapter.id === draggingChapterId,
          'drag-target': chapter.id === dragTargetChapterId
        }"
        draggable="true"
        @dragstart="handleDragStart($event, chapter.id)"
        @dragover="handleDragOver($event, chapter.id)"
        @drop="handleDrop(chapter.id)"
        @dragend="handleDragEnd"
      >
        <div class="chapter-item-main">
          <button
            v-if="chapter.id !== editingChapterId"
            type="button"
            class="chapter-select-button"
            @click="$emit('select', chapter.id)"
          >
            <span class="chapter-title-row">
              <span class="chapter-title">{{ buildChapterLabel(chapter) }}</span>
              <span
                v-if="resolveStateMarker(chapter.id)"
                class="chapter-state-marker"
                :data-state="resolveStateMarker(chapter.id)"
              >
                {{ resolveStateMarker(chapter.id) === 'conflict' ? '!' : '•' }}
              </span>
            </span>
            <span class="chapter-meta">
              {{ formatWords(chapter.word_count ?? chapter.current_word_count ?? estimateWords(chapter.content)) }} 字
            </span>
          </button>

          <form v-else class="chapter-rename-form" @submit.prevent="submitRename(chapter.id)">
            <input
              v-model="editingTitle"
              class="chapter-rename-input"
              type="text"
              maxlength="120"
              @keydown.esc.prevent="cancelRename"
              @blur="submitRename(chapter.id)"
            />
          </form>
        </div>

        <div class="chapter-actions">
          <button type="button" class="chapter-action-button" @click="startRename(chapter)">
            改名
          </button>
          <button type="button" class="chapter-action-button danger" @click="$emit('delete', chapter.id)">
            删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  chapters: {
    type: Array,
    default: () => []
  },
  activeChapterId: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  draftChapterIds: {
    type: Array,
    default: () => []
  },
  conflictChapterId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select', 'create', 'rename', 'delete', 'reorder', 'jump-invalid'])

const editingChapterId = ref('')
const editingTitle = ref('')
const draggingChapterId = ref('')
const dragTargetChapterId = ref('')
const searchQuery = ref('')
const jumpOrderInput = ref('')

const draftChapterIdSet = computed(() => new Set(
  (props.draftChapterIds || []).map((id) => String(id || '')).filter(Boolean)
))

const estimateWords = (content) => String(content || '').trim().length
const formatWords = (value) => Number(value || 0).toLocaleString('zh-CN')

const resolveOrderIndex = (chapter) => {
  const orderIndex = Number(chapter?.order_index)
  if (Number.isFinite(orderIndex) && orderIndex > 0) {
    return orderIndex
  }
  const index = props.chapters.findIndex((item) => item.id === chapter?.id)
  return index >= 0 ? index + 1 : 1
}

const buildChapterLabel = (chapter) => {
  const prefix = `第${resolveOrderIndex(chapter)}章`
  const title = String(chapter?.title || '').trim()
  return title ? `${prefix} ${title}` : prefix
}

const filteredChapters = computed(() => {
  const keyword = String(searchQuery.value || '').trim().toLowerCase()
  if (!keyword) return props.chapters
  return props.chapters.filter((chapter) => {
    const label = buildChapterLabel(chapter).toLowerCase()
    const content = String(chapter?.content || '').toLowerCase()
    return label.includes(keyword) || content.includes(keyword)
  })
})

const resolveStateMarker = (chapterId) => {
  const id = String(chapterId || '')
  if (!id) return ''
  if (String(props.conflictChapterId || '') === id) return 'conflict'
  if (draftChapterIdSet.value.has(id)) return 'draft'
  return ''
}

const handleCreate = () => {
  searchQuery.value = ''
  jumpOrderInput.value = ''
  emit('create')
}

const startRename = async (chapter) => {
  editingChapterId.value = String(chapter?.id || '')
  editingTitle.value = String(chapter?.title || '')
  await nextTick()
  const target = document.querySelector('.chapter-rename-input')
  target?.focus?.()
  target?.select?.()
}

const cancelRename = () => {
  editingChapterId.value = ''
  editingTitle.value = ''
}

const submitRename = (chapterId) => {
  const id = String(chapterId || '')
  const nextTitle = String(editingTitle.value || '').trim()
  if (!id) return
  if (!nextTitle) {
    cancelRename()
    return
  }
  emit('rename', { chapterId: id, title: nextTitle })
  cancelRename()
}

const moveChapterId = (chapterIds, sourceId, targetId) => {
  const nextIds = [...chapterIds]
  const sourceIndex = nextIds.indexOf(sourceId)
  const targetIndex = nextIds.indexOf(targetId)
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return []
  const [moved] = nextIds.splice(sourceIndex, 1)
  nextIds.splice(targetIndex, 0, moved)
  return nextIds
}

const handleDragStart = (event, chapterId) => {
  draggingChapterId.value = String(chapterId || '')
  dragTargetChapterId.value = ''
  event.dataTransfer?.setData('text/plain', draggingChapterId.value)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

const handleDragOver = (event, chapterId) => {
  if (!draggingChapterId.value || draggingChapterId.value === String(chapterId || '')) return
  event.preventDefault()
  dragTargetChapterId.value = String(chapterId || '')
}

const handleDrop = (chapterId) => {
  const targetId = String(chapterId || '')
  const sourceId = String(draggingChapterId.value || '')
  const orderedIds = moveChapterId(
    props.chapters.map((item) => String(item.id)),
    sourceId,
    targetId
  )
  if (orderedIds.length) emit('reorder', orderedIds)
  draggingChapterId.value = ''
  dragTargetChapterId.value = ''
}

const handleDragEnd = () => {
  draggingChapterId.value = ''
  dragTargetChapterId.value = ''
}

const submitJump = () => {
  const targetOrder = Number.parseInt(String(jumpOrderInput.value || '').trim(), 10)
  if (!Number.isInteger(targetOrder) || targetOrder <= 0) {
    emit('jump-invalid')
    return
  }
  const matched = props.chapters.find((chapter) => resolveOrderIndex(chapter) === targetOrder)
  if (!matched) {
    emit('jump-invalid')
    return
  }
  emit('select', matched.id)
  jumpOrderInput.value = ''
}

const scrollToChapter = (chapterId) => {
  const id = String(chapterId || '')
  if (!id) return
  const target = document.querySelector(`.chapter-item[data-chapter-id="${id}"]`)
  target?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
}

watch(
  () => props.activeChapterId,
  async (chapterId) => {
    await nextTick()
    scrollToChapter(chapterId)
  }
)

defineExpose({ scrollToChapter })
</script>

<style scoped>
.chapter-sidebar {
  --sidebar-bg: var(--studio-card-bg, var(--ink-surface-1, #ffffff));
  --sidebar-bg-soft: var(--studio-bg-focus, var(--ink-surface-2, #f8fafc));
  --sidebar-border: var(--studio-border, var(--ink-border, #e5e7eb));
  --sidebar-border-strong: var(--ink-border-strong, #d1d5db);
  --sidebar-title: var(--studio-title, var(--ink-text-primary, #111827));
  --sidebar-text: var(--studio-text, var(--ink-text-secondary, #4b5563));
  --sidebar-muted: var(--studio-muted, var(--ink-text-muted, #6b7280));
  --sidebar-accent: var(--ink-accent, #2563eb);
  --sidebar-accent-soft: var(--ink-accent-soft, #dbeafe);

  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--sidebar-title);
}

.sidebar-header p {
  margin-top: 6px;
  font-size: 12px;
  color: var(--sidebar-muted);
}

.add-button {
  border: 1px solid var(--sidebar-accent-soft);
  border-radius: 999px;
  background: color-mix(in srgb, var(--sidebar-accent-soft) 72%, var(--sidebar-bg));
  color: var(--sidebar-accent);
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.sidebar-tools {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.jump-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.sidebar-tool-input {
  width: 100%;
  border: 1px solid var(--sidebar-border-strong);
  border-radius: 12px;
  background: var(--sidebar-bg);
  padding: 10px 12px;
  font-size: 13px;
  color: var(--sidebar-title);
  outline: none;
}

.sidebar-tool-input:focus {
  border-color: var(--sidebar-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sidebar-accent) 18%, transparent);
}

.jump-button {
  border: 1px solid var(--sidebar-border-strong);
  border-radius: 12px;
  background: var(--sidebar-bg);
  padding: 0 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--sidebar-text);
  cursor: pointer;
}

.sidebar-state {
  margin-top: 18px;
  border-radius: 16px;
  background: var(--sidebar-bg-soft);
  padding: 14px;
  font-size: 13px;
  color: var(--sidebar-muted);
}

.chapter-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
  padding-right: 4px;
}

.chapter-item {
  border: 1px solid var(--sidebar-border);
  border-radius: 16px;
  background: var(--sidebar-bg);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.18s ease;
}

.chapter-item:hover {
  border-color: var(--sidebar-border-strong);
  background: var(--sidebar-bg-soft);
}

.chapter-item.active {
  border-color: var(--sidebar-accent-soft);
  background: color-mix(in srgb, var(--sidebar-accent-soft) 62%, var(--sidebar-bg));
}

.chapter-item.dragging {
  opacity: 0.7;
}

.chapter-item.drag-target {
  border-color: var(--sidebar-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--sidebar-accent) 16%, transparent);
}

.chapter-item-main {
  flex: 1;
  min-width: 0;
}

.chapter-select-button {
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--sidebar-title);
}

.chapter-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.chapter-state-marker {
  flex: none;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.chapter-state-marker[data-state='draft'] {
  color: var(--sidebar-accent);
}

.chapter-state-marker[data-state='conflict'] {
  color: var(--ink-danger-text, var(--ink-error));
}

.chapter-meta {
  font-size: 12px;
  color: var(--sidebar-muted);
}

.chapter-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease;
}

.chapter-item:hover .chapter-actions,
.chapter-item.editing .chapter-actions,
.chapter-item.active .chapter-actions {
  opacity: 1;
  pointer-events: auto;
}

.chapter-action-button {
  border: 1px solid var(--sidebar-accent-soft);
  border-radius: 999px;
  background: var(--sidebar-bg);
  color: var(--sidebar-accent);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.chapter-action-button.danger {
  border-color: var(--ink-danger-text, #dc2626);
  color: var(--ink-danger-text, #dc2626);
}

.chapter-rename-form {
  width: 100%;
}

.chapter-rename-input {
  width: 100%;
  border: 1px solid var(--sidebar-accent);
  border-radius: 12px;
  background: var(--sidebar-bg);
  padding: 8px 10px;
  font-size: 14px;
  color: var(--sidebar-title);
  outline: none;
}
</style>
