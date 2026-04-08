<template>
  <div class="workspace-page">
    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h2>结构台</h2>
          <p>从宏观视角掌控 Story Model、剧情弧、角色与世界观设定。</p>
        </div>
        <div class="header-actions">
          <el-button :loading="workspace.state.structureLoading" @click="workspace.refreshStructure">
            <el-icon><Refresh /></el-icon>刷新结构
          </el-button>
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

      <div v-if="workspace.state.activeArcs.length" class="arc-grid">
        <article v-for="arc in workspace.state.activeArcs" :key="arc.arc_id" class="arc-card">
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
import { computed } from 'vue'
import { Refresh, Document, DataLine, Connection } from '@element-plus/icons-vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const workspace = useWorkspaceContext()

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

const getArcStatusType = (status) => {
  switch (String(status).toLowerCase()) {
    case 'active': return 'primary'
    case 'dormant': return 'info'
    case 'completed': return 'success'
    case 'archived': return 'info'
    default: return 'warning'
  }
}
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  padding: 32px;
  background-color: #ffffff;
  height: 100%;
  overflow-y: auto;
  gap: 32px;
}

.workspace-section {
  display: flex;
  flex-direction: column;
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
  border-radius: 12px;
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
  