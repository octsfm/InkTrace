<template>
  <div class="workspace-page">
    <WorkspacePageHero
      eyebrow="结构"
      title="结构与剧情弧工作台"
      description="集中查看主线摘要、当前进度和活跃剧情弧，但不抢写作主流程的中心位置。"
    >
      <div class="hero-action">
        <el-button :loading="workspace.state.structureLoading" @click="workspace.refreshStructure">
          <el-icon><Refresh /></el-icon>刷新结构
        </el-button>
      </div>
    </WorkspacePageHero>

    <section class="workspace-section">
      <WorkspaceSectionHeader>
        <template #main>
          <div class="header-left">
            <h2>结构台</h2>
            <p>从宏观视角掌控故事模型、剧情弧、角色与世界观设定。</p>
          </div>
        </template>
      </WorkspaceSectionHeader>

      <WorkspaceSelectableChips :items="structureViewItems" :selected-key="activeStructureKey" />

      <div class="view-focus-banner">
        <div>
          <div class="view-focus-label">当前结构视角</div>
          <div class="view-focus-title">{{ activeStructureMeta.title }}</div>
          <div class="view-focus-desc">{{ activeStructureMeta.description }}</div>
        </div>
        <el-button
          v-if="activeStructureKey !== 'plot_arc'"
          plain
          @click="switchStructureView('plot_arc')"
        >
          回到剧情弧
        </el-button>
      </div>

      <WorkspaceSummaryChips :items="structureFocusSummaryItems" />
      <WorkspaceActionBar :items="workspaceActionItems" />
      <WorkspaceInfoBanner v-if="structureFocusBannerText" :text="structureFocusBannerText" tone="primary" />

      <div class="summary-grid">
        <article class="summary-card">
          <div class="card-header">
            <el-icon class="card-icon"><Document /></el-icon>
            <h3 class="card-title">主线摘要</h3>
          </div>
          <p class="card-content">{{ mainPlotText }}</p>
        </article>
        
        <article class="summary-card">
          <div class="card-header">
            <el-icon class="card-icon"><DataLine /></el-icon>
            <h3 class="card-title">当前进度</h3>
          </div>
          <p class="card-content">{{ currentProgress }}</p>
        </article>
        
        <article class="summary-card">
          <div class="card-header">
            <el-icon class="card-icon"><Connection /></el-icon>
            <h3 class="card-title">当前状态</h3>
          </div>
          <p class="card-content">{{ currentState }}</p>
        </article>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div class="header-left">
          <h3>{{ activeSectionTitle }}</h3>
          <p>{{ activeSectionDescription }}</p>
        </div>
      </div>

      <div v-if="priorityArc" class="priority-banner">
        <div>
          <div class="priority-label">{{ priorityBannerLabel }}</div>
          <div class="priority-title">{{ priorityArc.title || priorityArc.arc_id }}</div>
          <div class="priority-desc">{{ priorityBannerDescription }}</div>
        </div>
        <el-button type="primary" plain @click="focusArc(priorityArc)">
          {{ priorityActionLabel }}
        </el-button>
      </div>

      <div v-if="structureDecisionCards.length" class="decision-grid">
        <article
          v-for="item in structureDecisionCards"
          :key="item.key"
          class="decision-card"
        >
          <div class="decision-top">
            <span class="decision-tag">{{ item.tag }}</span>
            <span class="decision-cta">{{ item.cta }}</span>
          </div>
          <div class="decision-title">{{ item.title }}</div>
          <p class="decision-description">{{ item.description }}</p>
          <div class="decision-meta">{{ item.meta }}</div>
          <el-button size="small" type="primary" plain @click="item.onClick">
            {{ item.cta }}
          </el-button>
        </article>
      </div>

      <template v-if="activeStructureKey === 'plot_arc'">
        <WorkspaceSummaryChips :items="arcSummaryItems" />

        <WorkspaceSelectableChips :items="quickArcItems" :selected-key="focusedArcId" />

        <WorkspaceInfoBanner
          v-if="focusedArc"
          :text="`当前聚焦：${focusedArc.title || focusedArc.arc_id}`"
          tone="primary"
        />

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
                {{ arc.status || '未知' }}
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
      </template>

      <template v-else>
        <div class="lens-grid">
          <article
            v-for="card in structureLensCards"
            :key="card.title"
            class="lens-card"
          >
            <div class="lens-card-label">{{ card.label }}</div>
            <h4>{{ card.title }}</h4>
            <p>{{ card.description }}</p>
          </article>
        </div>

        <WorkspaceSelectableChips
          v-if="quickArcItems.length"
          :items="quickArcItems"
          :selected-key="focusedArcId"
        />

        <WorkspaceInfoBanner
          v-if="priorityArc"
          :text="`可继续查看关联剧情弧：${priorityArc.title || priorityArc.arc_id}`"
          tone="primary"
        />
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Refresh, Document, DataLine, Connection } from '@element-plus/icons-vue'
import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar.vue'
import WorkspaceInfoBanner from '@/components/workspace/WorkspaceInfoBanner.vue'
import WorkspacePageHero from '@/components/workspace/WorkspacePageHero.vue'
import WorkspaceSelectableChips from '@/components/workspace/WorkspaceSelectableChips.vue'
import WorkspaceSectionHeader from '@/components/workspace/WorkspaceSectionHeader.vue'
import WorkspaceSummaryChips from '@/components/workspace/WorkspaceSummaryChips.vue'
import { useWorkspaceStore } from '@/stores/workspace'


const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const arcCardRefs = ref({})

const structureViews = [
  { key: 'story_model', label: '故事模型' },
  { key: 'plot_arc', label: '剧情弧' },
  { key: 'character', label: '角色' },
  { key: 'worldview', label: '世界观' },
  { key: 'risk', label: '风险点' }
]

const structureMetaMap = {
  story_model: {
    title: '故事模型',
    description: '从故事模型层看当前小说的主线结构、推进阶段与全局关系。'
  },
  plot_arc: {
    title: '剧情弧',
    description: '从剧情弧层看当前最值得推进的主线和支线对象。'
  },
  character: {
    title: '角色视角',
    description: '从角色关系和人物弧层理解当前冲突、关系和角色状态。'
  },
  worldview: {
    title: '世界观视角',
    description: '从设定与规则层检查当前结构支撑是否完整。'
  },
  risk: {
    title: '风险点视角',
    description: '优先扫描结构风险、冲突断层和需要补充的关键约束。'
  }
}

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

const currentChapterId = computed(() => String(workspace.currentChapterId?.value || ''))
const currentChapter = computed(() => (
  (workspace.state.chapters || []).find((chapter) => String(chapter.id || '') === currentChapterId.value) || null
))
const currentChapterLabel = computed(() => {
  if (currentChapter.value?.title) {
    return currentChapter.value.title
  }
  if (currentChapter.value?.chapter_number) {
    return `第 ${currentChapter.value.chapter_number} 章`
  }
  return currentChapterId.value ? '当前章节' : '未打开章节'
})

const focusedArcId = computed(() => (
  workspaceStore.currentStructureSection === 'plot_arc' && workspaceStore.currentObject?.type === 'plot_arc'
    ? String(workspaceStore.currentObject?.arcId || '')
    : ''
))

const focusedArc = computed(() => (
  (workspace.state.activeArcs || []).find((arc) => arc.arc_id === focusedArcId.value) || null
))

const sortedArcs = computed(() => {
  const priorityMap = { core: 4, major: 3, normal: 2, minor: 1 }
  const stageMap = { climax: 5, escalation: 4, midgame: 3, early_push: 2, setup: 1 }
  return [...(workspace.state.activeArcs || [])].sort((a, b) => {
    const priorityDiff = (priorityMap[String(b.priority || '').toLowerCase()] || 0) - (priorityMap[String(a.priority || '').toLowerCase()] || 0)
    if (priorityDiff !== 0) return priorityDiff
    return (stageMap[String(b.stage || '').toLowerCase()] || 0) - (stageMap[String(a.stage || '').toLowerCase()] || 0)
  })
})

const priorityArc = computed(() => sortedArcs.value[0] || null)
const topArcList = computed(() => sortedArcs.value.slice(0, 4))
const mainArcCount = computed(() => (
  (workspace.state.activeArcs || []).filter((arc) => String(arc.arc_type || '').toLowerCase().includes('main')).length
))

const activeStructureKey = computed(() => workspaceStore.currentStructureSection || 'plot_arc')
const activeStructureMeta = computed(() => structureMetaMap[activeStructureKey.value] || structureMetaMap.plot_arc)
const activeSectionTitle = computed(() => {
  const titleMap = {
    story_model: '故事模型摘要',
    plot_arc: '活跃剧情弧',
    character: '角色关联线索',
    worldview: '世界观约束',
    risk: '结构风险扫描'
  }
  return titleMap[activeStructureKey.value] || '结构摘要'
})
const activeSectionDescription = computed(() => {
  const descMap = {
    story_model: '先确认主线结构、推进阶段与故事模型的整体约束。',
    plot_arc: '当前阶段正在推进或需要关注的剧情分支。',
    character: '结合当前活跃剧情弧，查看最可能受影响的人物关系与角色推进。',
    worldview: '结合当前结构状态，检查设定规则和世界观支撑是否完整。',
    risk: '优先查看当前最值得处理的结构风险、冲突断层和约束缺口。'
  }
  return descMap[activeStructureKey.value] || '查看当前结构对象。'
})
const priorityActionLabel = computed(() => (
  activeStructureKey.value === 'plot_arc' ? '聚焦该剧情弧' : '查看关联剧情弧'
))
const priorityBannerLabel = computed(() => (
  activeStructureKey.value === 'plot_arc' ? '优先推进弧' : '优先关联弧'
))
const priorityBannerDescription = computed(() => {
  if (!priorityArc.value) {
    return '当前最值得优先推进的结构对象。'
  }
  if (activeStructureKey.value === 'risk') {
    return priorityArc.value.summary || priorityArc.value.reason || '当前最值得优先排查的风险来源。'
  }
  if (activeStructureKey.value === 'character') {
    return priorityArc.value.summary || priorityArc.value.reason || '当前最容易受角色关系影响的主线对象。'
  }
  if (activeStructureKey.value === 'worldview') {
    return priorityArc.value.summary || priorityArc.value.reason || '当前最需要设定规则支撑的结构对象。'
  }
  if (activeStructureKey.value === 'story_model') {
    return priorityArc.value.summary || priorityArc.value.reason || '当前最适合回到故事模型中校准的主线对象。'
  }
  return priorityArc.value.summary || priorityArc.value.reason || '当前最值得优先推进的结构对象。'
})
const structureFocusSummaryItems = computed(() => {
  const items = [
    { label: '当前视角', value: activeStructureMeta.value.title },
    { label: '活跃弧', value: String(workspace.state.activeArcs.length || 0) },
    { label: '主线摘要', value: String(Array.isArray(workspace.state.memoryView?.main_plot_lines) ? workspace.state.memoryView.main_plot_lines.length : 0) }
  ]

  if (activeStructureKey.value === 'risk') {
    return [
      { label: '风险视角', value: '已开启', tone: 'warning' },
      { label: '优先对象', value: priorityArc.value?.title || '未识别' },
      { label: '当前状态', value: currentState.value.slice(0, 18) || '未生成' }
    ]
  }

  if (activeStructureKey.value === 'character') {
    return [
      { label: '角色视角', value: '已开启' },
      { label: '优先弧', value: priorityArc.value?.title || '未识别' },
      { label: '当前状态', value: currentState.value.slice(0, 18) || '未生成' }
    ]
  }

  if (activeStructureKey.value === 'worldview') {
    return [
      { label: '世界观视角', value: '已开启' },
      { label: '主线摘要', value: String(Array.isArray(workspace.state.memoryView?.main_plot_lines) ? workspace.state.memoryView.main_plot_lines.length : 0) },
      { label: '推进阶段', value: currentProgress.value.slice(0, 18) || '未生成' }
    ]
  }

  if (activeStructureKey.value === 'story_model') {
    return [
      { label: '故事模型', value: '已聚焦' },
      { label: '主线摘要', value: String(Array.isArray(workspace.state.memoryView?.main_plot_lines) ? workspace.state.memoryView.main_plot_lines.length : 0) },
      { label: '推进阶段', value: currentProgress.value.slice(0, 18) || '未生成' }
    ]
  }

  return items
})
const structureFocusBannerText = computed(() => {
  const bannerMap = {
    story_model: '当前适合先确认故事模型的主线与推进阶段，再决定要回到哪条剧情弧继续处理。',
    character: '当前视角更适合检查人物关系、角色动机和冲突承载是否与主线推进一致。',
    worldview: '当前视角更适合检查设定规则是否足够支撑当前冲突与剧情弧推进。',
    risk: '当前视角会优先提醒结构风险、冲突断层和需要补充的关键约束。'
  }
  return bannerMap[activeStructureKey.value] || ''
})
const structureLensCards = computed(() => {
  const cardsByView = {
    story_model: [
      {
        label: '主线结构',
        title: '当前故事模型主线',
        description: mainPlotText.value
      },
      {
        label: '推进阶段',
        title: '当前阶段判断',
        description: currentProgress.value
      },
      {
        label: '全局状态',
        title: '整体结构状态',
        description: currentState.value
      }
    ],
    character: [
      {
        label: '角色关系',
        title: '当前角色张力',
        description: currentState.value
      },
      {
        label: '关联主线',
        title: priorityArc.value?.title || '待确认关联剧情弧',
        description: priorityArc.value?.summary || '优先查看与角色关系最相关的剧情弧。'
      },
      {
        label: '推进建议',
        title: '角色推进建议',
        description: '先检查人物动机、关系变化和冲突承载是否与当前主线推进保持一致。'
      }
    ],
    worldview: [
      {
        label: '设定支撑',
        title: '当前设定状态',
        description: currentState.value
      },
      {
        label: '推进阶段',
        title: '当前推进对设定的要求',
        description: currentProgress.value
      },
      {
        label: '补强建议',
        title: '世界观补强建议',
        description: '优先确认规则边界、资源约束和世界反馈是否足够支撑当前冲突升级。'
      }
    ],
    risk: [
      {
        label: '风险扫描',
        title: '当前主要风险',
        description: currentState.value
      },
      {
        label: '优先对象',
        title: priorityArc.value?.title || '待确认风险对象',
        description: priorityArc.value?.summary || '优先回到最可能出现断层的剧情弧排查问题。'
      },
      {
        label: '处理建议',
        title: '结构修复建议',
        description: '优先检查冲突断层、约束缺失和推进失衡，再决定是否回到写作或任务台处理。'
      }
    ]
  }
  return cardsByView[activeStructureKey.value] || []
})
const structureDecisionCards = computed(() => {
  const cards = []

  if (priorityArc.value) {
    cards.push({
      key: 'priority-arc',
      tag: activeStructureKey.value === 'plot_arc' ? '主线' : '关联',
      cta: activeStructureKey.value === 'plot_arc' ? '聚焦' : '查看',
      title: priorityArc.value.title || priorityArc.value.arc_id,
      description: priorityBannerDescription.value,
      meta: `${priorityArc.value.stage || '未标注阶段'} · ${priorityArc.value.priority || '未标注优先级'}`,
      onClick: () => focusArc(priorityArc.value)
    })
  }

  if (currentChapterId.value) {
    cards.push({
      key: 'current-chapter',
      tag: '章节',
      cta: '返回',
      title: `回到 ${currentChapterLabel.value}`,
      description: '把当前结构判断带回正文或章节管理，继续推进具体内容落地。',
      meta: activeStructureKey.value === 'plot_arc' ? '结构 -> 写作' : `${activeStructureMeta.value.title} -> 写作`,
      onClick: () => workspace.openChapter?.(currentChapterId.value, 'writing')
    })
  }

  if (activeStructureKey.value === 'plot_arc') {
    cards.push({
      key: 'risk-lens',
      tag: '风险',
      cta: '切换',
      title: '切到风险点视角',
      description: '从当前剧情弧继续检查冲突断层、约束缺口和潜在失衡位置。',
      meta: currentState.value,
      onClick: () => switchStructureView('risk')
    })
    cards.push({
      key: 'character-lens',
      tag: '角色',
      cta: '切换',
      title: '切到角色视角',
      description: '检查人物动机、关系拉扯和角色推进是否仍与主线同步。',
      meta: currentProgress.value,
      onClick: () => switchStructureView('character')
    })
  } else {
    cards.push({
      key: 'plot-arc-return',
      tag: '剧情弧',
      cta: '回到',
      title: '回到剧情弧主视角',
      description: '把当前视角的判断重新落回具体剧情弧对象，继续做结构推进。',
      meta: priorityArc.value?.title || '当前优先对象',
      onClick: () => switchStructureView('plot_arc')
    })
  }

  return cards.slice(0, 3)
})
const workspaceActionItems = computed(() => ([
  {
    label: '回到概览',
    primary: true,
    onClick: () => workspace.openSection?.('overview')
  },
  ...(currentChapterId.value ? [{
    label: '回到当前章节',
    onClick: () => workspace.openChapter?.(currentChapterId.value, 'writing')
  }] : []),
  {
    label: '查看任务台',
    onClick: () => workspace.openSection?.('tasks')
  },
  ...(activeStructureKey.value !== 'plot_arc' ? [{
    label: '回到剧情弧',
    onClick: () => switchStructureView('plot_arc')
  }] : []),
  ...(priorityArc.value ? [{
    label: '聚焦优先弧',
    onClick: () => focusArc(priorityArc.value)
  }] : [])
]))
const structureViewItems = computed(() => (
  structureViews.map((item) => ({
    ...item,
    onClick: () => switchStructureView(item.key)
  }))
))
const quickArcItems = computed(() => (
  topArcList.value.map((arc) => ({
    key: arc.arc_id,
    label: arc.title || arc.arc_id,
    onClick: () => focusArc(arc)
  }))
))
const arcSummaryItems = computed(() => ([
  { label: '活跃弧', value: String(workspace.state.activeArcs.length || 0) },
  { label: '主线弧', value: String(mainArcCount.value) },
  { label: '当前聚焦', value: focusedArc.value?.title || '未聚焦' }
]))

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
  workspaceStore.focusPlotArc({
    arcId: arc?.arc_id || '',
    title: arc?.title || arc?.arc_id || ''
  }, { openView: false, section: 'plot_arc' })
}

const switchStructureView = (key) => {
  workspaceStore.setStructureSection(key)
  if (key !== 'plot_arc') {
    workspaceStore.setCurrentObject({
      type: key
    })
    return
  }
  if (priorityArc.value) {
    focusArc(priorityArc.value)
  }
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

.workspace-page :deep(.workspace-action-row) {
  margin-bottom: 18px;
}

.workspace-page :deep(.workspace-summary-row) {
  margin-bottom: 18px;
}

.view-focus-banner {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 18px;
  margin-bottom: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.view-focus-label {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
}

.view-focus-title {
  margin-top: 6px;
  font-size: 17px;
  font-weight: 600;
  color: #111827;
}

.view-focus-desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.workspace-page :deep(.workspace-selectable-row) {
  margin-bottom: 18px;
}

.summary-card {
  padding: 20px;
  border-radius: 16px;
  background-color: #F9FAFB;
  border: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.summary-card:hover,
.decision-card:hover,
.lens-card:hover {
  transform: translateY(-1px);
  border-color: #D1D5DB;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
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

.lens-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.lens-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
}

.lens-card-label {
  font-size: 11px;
  font-weight: 600;
  color: #2563EB;
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  border-radius: 999px;
  padding: 3px 8px;
  width: fit-content;
}

.lens-card h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.lens-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
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

.workspace-page :deep(.workspace-info-banner) {
  margin-bottom: 16px;
}

.decision-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.decision-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.decision-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.decision-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2563EB;
  background-color: #EFF6FF;
  border: 1px solid #DBEAFE;
  border-radius: 999px;
  padding: 3px 8px;
}

.decision-cta {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
}

.decision-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.decision-description {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.decision-meta {
  font-size: 12px;
  color: #9CA3AF;
}

.priority-banner {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 18px;
  margin-bottom: 18px;
  border-radius: 18px;
  border: 1px solid #DDD6FE;
  background: linear-gradient(180deg, #F8FAFC 0%, #F5F3FF 100%);
}

.priority-label {
  font-size: 11px;
  font-weight: 600;
  color: #7C3AED;
}

.priority-title {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.priority-desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
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
  .summary-grid,
  .decision-grid,
  .lens-grid {
    grid-template-columns: 1fr;
  }

  .page-hero {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .workspace-page {
    padding: 20px;
    gap: 24px;
  }

  .workspace-section {
    padding: 20px;
  }

  .view-focus-banner,
  .priority-banner,
  .arc-top,
  .arc-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
