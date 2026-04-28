<template>
  <div class="chapter-sidebar">
    <div class="sidebar-header">
      <div>
        <h2>章节列表</h2>
        <p>{{ chapters.length }} 章</p>
      </div>
      <button type="button" class="add-button" @click="$emit('create')">+ 新章</button>
    </div>

    <div v-if="loading" class="sidebar-state">正在加载章节...</div>
    <div v-else-if="!chapters.length" class="sidebar-state">当前还没有章节。</div>
    <div v-else class="chapter-list">
      <button
        v-for="chapter in chapters"
        :key="chapter.id"
        type="button"
        class="chapter-item"
        :class="{ active: chapter.id === activeChapterId }"
        @click="$emit('select', chapter.id)"
      >
        <span class="chapter-title">{{ chapter.title || `第${chapter.chapter_number || chapter.number || 0}章` }}</span>
        <span class="chapter-meta">{{ formatWords(chapter.word_count ?? chapter.current_word_count ?? estimateWords(chapter.content)) }} 字</span>
      </button>
    </div>

    <div class="sidebar-footer">
      <p>重命名、删除和拖拽排序将在后续步骤接入。</p>
    </div>
  </div>
</template>

<script setup>
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
  }
})

defineEmits(['select', 'create'])

const estimateWords = (content) => String(content || '').trim().length
const formatWords = (value) => Number(value || 0).toLocaleString('zh-CN')
</script>

<style scoped>
.chapter-sidebar {
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
  color: #111827;
}

.sidebar-header p {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}

.add-button {
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.sidebar-state {
  margin-top: 18px;
  border-radius: 16px;
  background: #f9fafb;
  padding: 14px;
  font-size: 13px;
  color: #6b7280;
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
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #ffffff;
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.18s ease;
}

.chapter-item:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.chapter-item.active {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.chapter-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.chapter-meta {
  font-size: 12px;
  color: #6b7280;
}

.sidebar-footer {
  margin-top: 16px;
  font-size: 12px;
  line-height: 1.7;
  color: #6b7280;
}
</style>
