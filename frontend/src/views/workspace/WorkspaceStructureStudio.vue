<template>
  <div class="workspace-page">
    <section class="page-hero">
      <div class="hero-copy">
        <div class="hero-eyebrow">Structure</div>
        <h1>结构与剧情弧工作台</h1>
        <p>集中查看主线摘要、当前进度和活跃剧情弧，但不抢写作主流程的中心位置。</p>
      </div>
      <div class="hero-action">
        <el-button :loading="workspace.state.structureLoading" @click="workspace.refreshStructure">
          <el-icon><Refresh /></el-icon>刷新结构
        </el-button>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h2>结构台</h2>
          <p>从宏观视角掌控 Story Model、剧情弧、角色与世界观设定。</p>
        </div>
      </div>

      <div class="summary-grid">
        <article class="summary-card">
          <div class="card-header">
            <el-icon class="card-icon"><Document /></el-icon>
            <h3 class="card-title">主线摘要 (Main Plot)</h3>
          </div>
          <p class="card-content">{{ mainPlotText }}</p>
        </article>
        
        <article class="summary-card">
          <div class="card-header">
            <el-icon class="card-icon"><DataLine /></el-icon>
            <h3 class="card-title">当前进度 (Progress)</h3>
          </div>
          <p class="card-content">{{ currentProgress }}</p>
        </article>
        
        <article class="summary-card">
          <div class="card-header">
            <el-icon class="card-icon"><Connection /></el-icon>
            <h3 class="card-title">当前状态 (State)</h3>
          </div>
          <p class="card-content">{{ currentState }}</p>
        </article>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h3>活跃剧情弧 (Active Plot Arcs)</h3>
          <p>当前阶段正在推进或需要关注的剧情分支。</p>
        </div>
      </div>

      <div v-if="focusedArc" class="focus-banner">
        当前聚焦：{{ focusedArc.title || focusedArc.arc_id }}
      </div>

      <div v-if="workspace.state.activeArcs.length" class="arc-grid">
        <article
          v-for="arc in workspace.state.activeArcs"
          :key="arc.arc_id"
          :ref="(el) => setArcCardRef(arc.arc_id, el)"
          class="arc-card"
          :class="{ focused: focusedArcId === arc.arc_id }"
          :data-arc-id="arc.arc_id"
          @click="focusArc(arc)"
        >
          <div class="arc-top">
            <div class="arc-title-area">
              <h4>{{ arc.title || arc.arc_id }}</h4>
              <span class="arc-type">{{ arc.arc_type || '未标注类型' }}</span>
            </div>
            <el-tag size="small" :type="getArcStatusType(arc.status)" effect="plain">
              {{ arc.status || 'unknown' }}
            </el-tag>
          </div>
          <p class="arc-desc">{{ arc.summary || arc.reason || '当前没有更详细的剧情弧摘要。' }}</p>
          <div class="arc-meta">
            <div class="meta-item">
              <span class="meta-label">阶段</span>
              <span class="meta-value">{{ arc.stage || '未标注' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">优先级</span>
              <span class="meta-value">{{ arc.priority || '未标注' }}</span>
            </div>
          </div>
        </article>
      </div>
      <el-empty v-else description="当前没有活跃的剧情弧。" />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Refresh, Document, DataLine, Connection } from '@element-plus/icons-vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const arcCardRefs = ref({})

const mainPlotText = computed(() => {
  const lines = Array.isArray(workspace.state.memoryView?.main_plot_lines)
    ? workspace.state.memoryView.main_plot_lines
    : []
  return lines.length ? lines.join('；') : '当前还没有形成稳定的主线摘要。'
})

const currentProgress = computed(() => (
  workspace.state.memoryView?.current_progress || '当前还没有稳定的章节推进摘要。'
))

const currentState = computed(() => (
  workspace.state.memoryView?.current_state || '当前还没有可展示的结构状态。'
))

const focusedArcId = computed(() => (
  workspaceStore.currentStructureSection === 'plot_arc' && workspaceStore.currentObject?.type === 'plot_arc'
    ? String(workspaceStore.currentObject?.arcId || '')
    : ''
))

const focusedArc = computed(() => (
  (workspace.state.activeArcs || []).find((arc) => arc.arc_id === focusedArcId.value) || null
))

const setArcCardRef = (arcId, el) => {
  if (!arcId) return
  if (!el) {
    delete arcCardRefs.value[arcId]
    return
  }
  arcCardRefs.value[arcId] = el
}

const scrollToFocusedArc = async (arcId) => {
  if (!arcId) return
  await nextTick()
  const element = arcCardRefs.value[arcId]
  if (element?.scrollIntoView) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

const focusArc = (arc) => {
  workspaceStore.setStructureSection('plot_arc')
  workspaceStore.setCurrentObject({
    type: 'plot_arc',
    arcId: arc?.arc_id || '',
    title: arc?.title || arc?.arc_id || ''
  })
}

const getArcStatusType = (status) => {
  switch (String(status).toLowerCase()) {
    case 'active': return 'primary'
    case 'dormant': return 'info'
    case 'completed': return 'success'
    case 'archived': return 'info'
    default: return 'warning'
  }
}

watch(
  () => focusedArcId.value,
  (arcId) => {
    if (!arcId) return
    void scrollToFocusedArc(arcId)
  },
  { immediate: true }
)
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  padding: 32px;
  background-color: #F8FAFC;
  height: 100%;
  overflow-y: auto;
  gap: 32px;
}

.page-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  border-radius: 24px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-eyebrow {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.page-hero h1 {
  font-size: 28px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.page-hero p {
  margin: 0;
  max-width: 760px;
  font-size: 14px;
  line-height: 1.7;
  color: #4B5563;
}

.workspace-section {
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-left h2, .header-left h3 {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.header-left h3 {
  font-size: 20px;
}

.header-left p {
  font-size: 14px;
  color: #6B7280;
  margin: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.summary-card {
  padding: 20px;
  border-radius: 16px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  font-size: 18px;
  color: #6366F1;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.card-content {
  font-size: 14px;
  color: #4B5563;
  line-height: 1.5;
  margin: 0;
}

.arc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.arc-card {
  padding: 16px;
  border-radius: 16px;
  background-color: #FFFFFF;
  border: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.arc-card:hover {
  border-color: #D1D5DB;
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
}

.arc-card.focused {
  border-color: #C4B5FD;
  background: linear-gradient(180deg, #FFFFFF 0%, #F5F3FF 100%);
  box-shadow: 0 16px 28px rgba(124, 58, 237, 0.10);
}

.focus-banner {
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #DDD6FE;
  background-color: #F5F3FF;
  color: #6D28D9;
  font-size: 13px;
  font-weight: 600;
}

.arc-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.arc-title-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.arc-title-area h4 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.arc-type {
  font-size: 12px;
  color: #6B7280;
}

.arc-desc {
  font-size: 14px;
  color: #4B5563;
  line-height: 1.5;
  margin: 0;
}

.arc-meta {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-label {
  font-size: 12px;
  color: #9CA3AF;
}

.meta-value {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
}

@media (max-width: 1100px) {
  .page-hero,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .page-hero {
    flex-direction: column;
  }
}
</style>
