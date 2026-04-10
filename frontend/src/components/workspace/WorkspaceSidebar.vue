<template>
  <aside class="workspace-sidebar">
    <div class="sidebar-intro">
      <div class="sidebar-eyebrow">{{ resolvedSidebarMeta.eyebrow }}</div>
      <div class="sidebar-title">{{ resolvedSidebarMeta.title }}</div>
      <div class="sidebar-subtitle">{{ resolvedSidebarMeta.subtitle }}</div>
    </div>

    <!-- Writing View: Chapter Tree -->
    <section v-if="activeView === 'writing' || activeView === 'chapters'" class="sidebar-section chapter-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">章节目录</div>
        <button type="button" class="ghost-action" @click="emit('create-chapter')">
          <el-icon><Plus /></el-icon>
        </button>
      </div>

      <el-input
        v-model="chapterKeyword"
        class="sidebar-search"
        size="small"
        placeholder="搜索章节"
        clearable
      />

      <div v-if="!chapterItems.length" class="sidebar-empty">
        还没有章节，先从导入内容或新建章节开始。
      </div>

      <div v-else class="chapter-list">
        <button
          v-for="chapter in filteredChapters"
          :key="chapter.id"
          type="button"
          class="chapter-item"
          :class="{ active: activeChapterId === chapter.id }"
          @click="emit('open-chapter', chapter.id)"
        >
          <div class="chapter-number">第 {{ chapter.chapter_number || '?' }} 章</div>
          <div class="chapter-title">{{ chapter.title || '未命名章节' }}</div>
          <div class="chapter-meta">
            <span>{{ chapter.updated_at ? formatDate(chapter.updated_at) : '未记录更新时间' }}</span>
          </div>
        </button>
      </div>
    </section>

    <!-- Structure View: Object Navigation -->
    <section v-else-if="activeView === 'structure'" class="sidebar-section structure-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">结构导航</div>
      </div>
      <div class="nav-list">
        <button
          v-for="item in resolvedStructureItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeStructureSection === item.key }"
          @click="emit('change-structure', item.key)"
        >
          {{ item.label }}
        </button>
      </div>
    </section>

    <!-- Tasks View: Task Filter Navigation -->
    <section v-else-if="activeView === 'tasks'" class="sidebar-section tasks-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">任务视图</div>
      </div>
      <div class="nav-list">
        <button
          v-for="item in resolvedTaskFilters"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeTaskFilter === item.key }"
          @click="emit('change-task-filter', item.key)"
        >
          {{ item.label }}
        </button>
      </div>
    </section>
    
    <!-- Overview View: Outline/Info -->
    <section v-else-if="activeView === 'overview'" class="sidebar-section overview-section">
      <div class="sidebar-heading-row">
        <div class="sidebar-heading">概览导航</div>
      </div>
      <div class="nav-list">
        <div
          v-for="item in resolvedOverviewCards"
          :key="item.label"
          class="overview-card"
        >
          <div class="overview-label">{{ item.label }}</div>
          <div class="overview-value">{{ item.value }}</div>
        </div>
      </div>
    </section>

  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { Plus } from '@element-plus/icons-vue'

const props = defineProps({
  currentView: {
    type: String,
    default: ''
  },
  currentChapterId: {
    type: String,
    default: ''
  },
  currentStructureSection: {
    type: String,
    default: ''
  },
  currentTaskFilter: {
    type: String,
    default: ''
  },
  chapters: {
    type: Array,
    default: () => []
  },
  sidebarMeta: {
    type: Object,
    default: () => null
  },
  structureItems: {
    type: Array,
    default: () => []
  },
  taskFilters: {
    type: Array,
    default: () => []
  },
  overviewCards: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['open-chapter', 'create-chapter', 'change-structure', 'change-task-filter'])

const workspaceStore = useWorkspaceStore()
const { state, currentChapterId } = useWorkspaceContext()
const chapterKeyword = ref('')

const structureItems = [
  { key: 'story_model', label: 'Story Model' },
  { key: 'plot_arc', label: '剧情弧 PlotArc' },
  { key: 'character', label: '角色 Characters' },
  { key: 'worldview', label: '世界观 Worldview' },
  { key: 'risk', label: '风险点 Risks' }
]

const taskFilters = [
  { key: 'all', label: '全部任务' },
  { key: 'running', label: '运行中' },
  { key: 'failed', label: '失败' },
  { key: 'completed', label: '已完成' },
  { key: 'audit', label: '审查' }
]

const activeView = computed(() => props.currentView || workspaceStore.currentView)
const activeChapterId = computed(() => props.currentChapterId || currentChapterId.value || '')
const activeStructureSection = computed(() => props.currentStructureSection || workspaceStore.currentStructureSection)
const activeTaskFilter = computed(() => props.currentTaskFilter || workspaceStore.currentTaskFilter)
const chapterItems = computed(() => (Array.isArray(props.chapters) && props.chapters.length ? props.chapters : (state.chapters || [])))
const resolvedStructureItems = computed(() => (Array.isArray(props.structureItems) && props.structureItems.length ? props.structureItems : structureItems))
const resolvedTaskFilters = computed(() => (Array.isArray(props.taskFilters) && props.taskFilters.length ? props.taskFilters : taskFilters))

const filteredChapters = computed(() => {
  const keyword = chapterKeyword.value.trim().toLowerCase()
  const chapters = Array.isArray(chapterItems.value) ? [...chapterItems.value] : []
  const sorted = chapters.sort((a, b) => (a.chapter_number || 0) - (b.chapter_number || 0))
  if (!keyword) {
    return sorted
  }

  return sorted.filter((chapter) => {
    const title = String(chapter.title || '').toLowerCase()
    const chapterNo = String(chapter.chapter_number || '')
    return title.includes(keyword) || chapterNo.includes(keyword)
  })
})

const latestChapterLabel = computed(() => {
  const chapter = [...(state.chapters || [])].sort((a, b) => {
    const aTs = a.updated_at ? new Date(a.updated_at).getTime() : 0
    const bTs = b.updated_at ? new Date(b.updated_at).getTime() : 0
    return bTs - aTs
  })[0]
  if (!chapter) return '暂无章节'
  return chapter.title || `第 ${chapter.chapter_number || '?'} 章`
})

const taskStatusLabel = computed(() => {
  const status = String(state.organizeProgress?.status || '').trim()
  if (!status) return '暂无任务'
  if (status === 'running') return '整理中'
  if (status === 'failed' || status === 'error') return '最近失败'
  if (status === 'success' || status === 'done') return '最近完成'
  return status
})

const sidebarMetaMap = {
  writing: {
    eyebrow: 'Writing',
    title: '章节与对象导航',
    subtitle: '当前以章节为主对象，切换章节不会离开工作区。'
  },
  chapters: {
    eyebrow: 'Chapters',
    title: '章节导航',
    subtitle: '统一查看章节对象，再按需进入写作或管理视图。'
  },
  structure: {
    eyebrow: 'Structure',
    title: '结构导航',
    subtitle: '在剧情弧、角色与世界观对象之间切换。'
  },
  tasks: {
    eyebrow: 'Tasks',
    title: '任务筛选',
    subtitle: '优先处理失败任务和审查结果。'
  },
  overview: {
    eyebrow: 'Overview',
    title: '项目摘要',
    subtitle: '只展示最小必要信息，帮助你决定下一步。'
  }
}

const resolvedSidebarMeta = computed(() => props.sidebarMeta || sidebarMetaMap[activeView.value] || sidebarMetaMap.overview)
const resolvedOverviewCards = computed(() => (
  Array.isArray(props.overviewCards) && props.overviewCards.length
    ? props.overviewCards
    : [
        { label: '当前小说', value: state.novel?.title || '未命名小说' },
        { label: '最近章节', value: latestChapterLabel.value },
        { label: '当前任务', value: taskStatusLabel.value }
      ]
))

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
  gap: 18px;
  height: 100%;
  width: 240px;
  padding: 20px 16px 16px;
  background-color: #F8FAFC;
  border-right: 1px solid #E5E7EB;
}

.sidebar-intro {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.sidebar-eyebrow {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sidebar-title {
  margin-top: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.sidebar-subtitle {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: #6B7280;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.sidebar-search {
  margin-bottom: 4px;
}

.sidebar-heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.sidebar-heading {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ghost-action {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  color: #6B7280;
  cursor: pointer;
  padding: 6px;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.ghost-action:hover {
  background-color: #F9FAFB;
  border-color: #D1D5DB;
  color: #374151;
}

.chapter-list, .nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow-y: auto;
}

.chapter-item, .nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: none;
  background: #FFFFFF;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-item {
  flex-direction: row;
  align-items: center;
  color: #4B5563;
  font-size: 14px;
  font-weight: 500;
}

.chapter-item:hover, .nav-item:hover {
  background-color: #F9FAFB;
  transform: translateY(-1px);
}

.chapter-item.active, .nav-item.active {
  background-color: #EFF6FF;
  color: #1D4ED8;
  box-shadow: inset 0 0 0 1px #DBEAFE;
}

.chapter-item.active .chapter-title {
  color: #1D4ED8;
}

.chapter-item.active .chapter-number,
.chapter-item.active .chapter-meta {
  color: #60A5FA;
}

.chapter-number {
  font-size: 12px;
  color: #9CA3AF;
}

.chapter-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  line-height: 1.4;
}

.chapter-meta {
  font-size: 12px;
  color: #9CA3AF;
}

.sidebar-empty {
  padding: 16px 12px;
  font-size: 13px;
  color: #6B7280;
  background-color: #F9FAFB;
  border-radius: 14px;
  text-align: center;
  border: 1px dashed #E5E7EB;
}

.overview-card {
  padding: 14px;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  background-color: #F9FAFB;
}

.overview-label {
  font-size: 12px;
  color: #9CA3AF;
  margin-bottom: 6px;
}

.overview-value {
  font-size: 14px;
  line-height: 1.5;
  color: #111827;
  font-weight: 500;
}
</style>
