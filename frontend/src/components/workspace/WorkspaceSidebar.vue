<template>
  <aside class="workspace-sidebar">
    <section class="sidebar-section">
      <div class="sidebar-heading">工作区</div>
      <button
        v-for="item in sectionItems"
        :key="item.key"
        type="button"
        class="nav-item"
        :class="{ active: currentSection === item.key }"
        @click="$emit('navigate', item.key)"
      >
        <span class="nav-label">{{ item.label }}</span>
        <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
      </button>
    </section>

    <section class="sidebar-section chapter-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">章节目录</div>
        <button type="button" class="ghost-action" @click="$emit('create-chapter')">新建</button>
      </div>

      <div v-if="!chapters.length" class="sidebar-empty">
        还没有章节，先从导入内容或新建章节开始。
      </div>

      <div v-else class="chapter-list">
        <button
          v-for="chapter in chapters"
          :key="chapter.id"
          type="button"
          class="chapter-item"
          :class="{ active: selectedChapterId === chapter.id }"
          @click="$emit('open-chapter', chapter.id)"
        >
          <div class="chapter-number">第 {{ chapter.chapter_number || '?' }} 章</div>
          <div class="chapter-title">{{ chapter.title || '未命名章节' }}</div>
          <div class="chapter-meta">
            <span>{{ chapter.updated_at ? formatDate(chapter.updated_at) : '未记录更新时间' }}</span>
          </div>
        </button>
      </div>
    </section>
  </aside>
</template>

<script setup>
defineProps({
  sectionItems: {
    type: Array,
    default: () => []
  },
  currentSection: {
    type: String,
    default: 'overview'
  },
  chapters: {
    type: Array,
    default: () => []
  },
  selectedChapterId: {
    type: String,
    default: ''
  }
})

defineEmits(['navigate', 'open-chapter', 'create-chapter'])

const formatDate = (value) => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric'
    })
  } catch (error) {
    return ''
  }
}
</script>

<style scoped>
.workspace-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  padding: 20px 16px;
  background:
    radial-gradient(circle at top left, rgba(233, 191, 130, 0.25), transparent 30%),
    linear-gradient(180deg, #f6f0e7 0%, #efe6d7 100%);
  border-right: 1px solid rgba(76, 59, 40, 0.08);
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-section {
  min-height: 0;
  flex: 1;
}

.sidebar-heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-heading {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7d654a;
}

.nav-item,
.chapter-item,
.ghost-action {
  border: none;
  background: none;
  font: inherit;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 14px;
  color: #49382a;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.nav-item:hover,
.chapter-item:hover,
.ghost-action:hover {
  background: rgba(255, 255, 255, 0.72);
}

.nav-item.active {
  background: #fffdf8;
  box-shadow: 0 10px 26px rgba(91, 62, 24, 0.12);
  transform: translateX(2px);
}

.nav-label {
  font-weight: 600;
}

.nav-badge {
  min-width: 22px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(162, 87, 38, 0.12);
  color: #a25726;
  font-size: 12px;
}

.ghost-action {
  padding: 6px 10px;
  border-radius: 999px;
  color: #8b6741;
  cursor: pointer;
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.chapter-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  text-align: left;
  color: #4b3a2b;
  cursor: pointer;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.chapter-item.active {
  background: #fffdf8;
  box-shadow: 0 10px 24px rgba(91, 62, 24, 0.12);
}

.chapter-number {
  font-size: 12px;
  color: #9d7b58;
}

.chapter-title {
  font-weight: 600;
  line-height: 1.45;
}

.chapter-meta {
  font-size: 12px;
  color: #9d7b58;
}

.sidebar-empty {
  padding: 16px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  color: #7d654a;
  line-height: 1.6;
}
</style>
