<template>
  <div class="workspace-page">
    <section class="workspace-section">
      <div class="section-header">
        <div>
          <h2>结构台</h2>
          <p>第一阶段先把 Story Model 摘要、活跃剧情弧和当前进度集中起来展示。</p>
        </div>
        <el-button :loading="workspace.state.structureLoading" @click="workspace.refreshStructure">刷新结构</el-button>
      </div>

      <div class="summary-grid">
        <article class="summary-card">
          <div class="card-title">主线摘要</div>
          <p>{{ mainPlotText }}</p>
        </article>
        <article class="summary-card">
          <div class="card-title">当前进度</div>
          <p>{{ currentProgress }}</p>
        </article>
        <article class="summary-card">
          <div class="card-title">当前状态</div>
          <p>{{ currentState }}</p>
        </article>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div>
          <h3>活跃剧情弧</h3>
          <p>第一阶段先用结构卡片承载，后续再升级为看板和可视化关系图。</p>
        </div>
      </div>

      <div v-if="workspace.state.activeArcs.length" class="arc-grid">
        <article v-for="arc in workspace.state.activeArcs" :key="arc.arc_id" class="arc-card">
          <div class="arc-top">
            <div>
              <h4>{{ arc.title || arc.arc_id }}</h4>
              <div class="arc-type">{{ arc.arc_type || '未标注类型' }}</div>
            </div>
            <el-tag size="small">{{ arc.status || 'unknown' }}</el-tag>
          </div>
          <p>{{ arc.summary || arc.reason || '当前没有更详细的剧情弧摘要。' }}</p>
          <div class="arc-meta">
            <span>阶段：{{ arc.stage || '未标注阶段' }}</span>
            <span>优先级：{{ arc.priority || '未标注' }}</span>
          </div>
        </article>
      </div>
      <el-empty v-else description="当前还没有可用的剧情弧。" />
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.workspace-section {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 34px rgba(93, 72, 37, 0.07);
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-header h2,
.section-header h3 {
  color: #342318;
}

.section-header p,
.summary-card p,
.arc-card p {
  margin-top: 8px;
  line-height: 1.7;
  color: #6f5641;
}

.summary-grid,
.arc-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.arc-card {
  padding: 18px;
  border-radius: 18px;
  background: #fff9f1;
}

.card-title {
  font-weight: 700;
  color: #3a291c;
}

.arc-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.arc-top h4 {
  color: #3a291c;
}

.arc-type,
.arc-meta {
  margin-top: 8px;
  color: #8b6f54;
}

.arc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
}

@media (max-width: 1200px) {
  .summary-grid,
  .arc-grid {
    grid-template-columns: 1fr;
  }
}
</style>
