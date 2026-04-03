<template>
  <div class="novel-write-page" v-loading="state.loading">
    <el-page-header content="续写工作台" @back="goBack" />

    <el-alert v-if="state.errorMessage" :title="state.errorMessage" type="error" show-icon :closable="false" />

    <el-row :gutter="16" class="section-grid">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>当前小说概览区</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="当前最新章节号">{{ latestChapterNumber }}</el-descriptions-item>
            <el-descriptions-item label="最新章节标题">{{ latestChapterTitle }}</el-descriptions-item>
            <el-descriptions-item label="当前主线摘要">{{ mainPlotSummary }}</el-descriptions-item>
            <el-descriptions-item label="当前写作焦点">{{ writingFocus }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>分支区</span>
              <el-button type="primary" :loading="state.branchLoading" @click="generateBranches">生成分支</el-button>
            </div>
          </template>
          <div v-if="!state.branches.length" class="empty-text">进入页面后不会自动生成分支，请手动点击“生成分支”。</div>
          <el-radio-group v-else v-model="state.selectedBranchId" class="branch-list">
            <el-radio
              v-for="branch in state.branches"
              :key="branch.id"
              :label="branch.id"
              border
              class="branch-card"
            >
              <div class="branch-title">{{ branch.title || '未命名分支' }}</div>
              <div class="branch-summary">{{ branch.summary || '暂无摘要' }}</div>
              <div class="branch-conflict">{{ branch.core_conflict || branch.conflict || '暂无核心冲突' }}</div>
              <div class="branch-conflict">{{ branch.style_tags || branch.style_hint || '暂无风格标签' }}</div>
            </el-radio>
          </el-radio-group>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>计划区</span>
          </template>
          <el-alert
            v-if="assistantPresetText"
            :title="assistantPresetText"
            type="success"
            show-icon
            :closable="false"
          />
          <el-form inline>
            <PlanningModeToggle v-model="state.planningMode" />
            <ArcListPanel v-model="state.targetArcId" :arcs="activeArcs" />
            <el-form-item label="续写章节数">
              <el-input-number v-model="state.chapterCount" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="每章目标字数">
              <el-input-number v-model="state.targetWords" :min="1000" :step="100" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="state.planLoading" @click="generatePlans">生成章节计划</el-button>
            </el-form-item>
          </el-form>
          <ArcSummaryCard
            class="top-gap"
            :planning-reason="planningReason"
            :stage-before="arcStageBefore"
            :stage-after-expected="arcStageAfterExpected"
            :stage-after-actual="arcStageAfterActual"
            :stage-advanced="arcStageAdvanced"
          />
          <el-table :data="state.plans" border style="width: 100%">
            <el-table-column prop="chapter_number" label="章节号" width="90" />
            <el-table-column prop="title" label="标题" min-width="160" />
            <el-table-column prop="chapter_function_label" label="章节功能" min-width="120" />
            <el-table-column prop="goal" label="本章目标" min-width="180" />
            <el-table-column prop="ending_hook" label="结尾钩子" min-width="180" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>预览区</span>
              <el-button type="primary" :loading="state.previewLoading" @click="previewFirstPlan">预览一章</el-button>
            </div>
          </template>
          <el-alert title="预览一章：仅生成草稿供查看，不会保存到章节列表。" type="info" show-icon :closable="false" />
          <ChapterTaskCard :task="state.previewResult.chapterTask || {}" />
          <ContextSourcePanel :context="previewContext" :task="state.previewResult.chapterTask || {}" class="top-gap" />
          <DraftPreviewTabs
            class="top-gap"
            title="预览结果"
            v-model:active-tab="previewDraftTab"
            :structural-draft="state.previewResult.structuralDraft"
            :detemplated-draft="state.previewResult.detemplatedDraft"
            :integrity-check="state.previewResult.integrityCheck"
            :revision-attempts="state.previewResult.revisionAttempts"
            :used-structural-fallback="state.previewResult.usedStructuralFallback"
            @apply="applyPreviewDraft"
            @save-draft="applyPreviewDraft"
            @discard="discardPreviewDraft"
          />
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>提交区</span>
              <el-button type="primary" :loading="state.commitLoading" @click="commitBatch">保存并继续生成</el-button>
            </div>
          </template>
          <el-alert title="保存并继续生成：按当前计划批量落库，生成后会更新详情页章节列表。" type="warning" show-icon :closable="false" />
          <el-alert
            v-if="batchStatusText"
            :title="batchStatusText"
            :type="state.generatedBatch.memoryRefreshed ? 'success' : 'warning'"
            show-icon
            :closable="false"
          />
          <GeneratedChapterList
            class="top-gap"
            :generated-chapters="normalizedGeneratedChapters"
            @view="viewGeneratedChapter"
            @edit="goToGeneratedChapter"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { novelApi, projectApi } from '@/api'
import ChapterTaskCard from '@/components/story/ChapterTaskCard.vue'
import ContextSourcePanel from '@/components/story/ContextSourcePanel.vue'
import DraftPreviewTabs from '@/components/story/DraftPreviewTabs.vue'
import GeneratedChapterList from '@/components/story/GeneratedChapterList.vue'
import ArcListPanel from '@/components/story/ArcListPanel.vue'
import ArcSummaryCard from '@/components/story/ArcSummaryCard.vue'
import PlanningModeToggle from '@/components/story/PlanningModeToggle.vue'
import { useNovelWriteState } from '@/composables/useNovelWriteState'
import { formatChapterFunction } from '@/constants/display'

const route = useRoute()
const router = useRouter()
const state = useNovelWriteState()
const projectId = ref('')
const novel = ref(null)
const memoryView = ref({})
const activeArcs = ref([])
const previewContext = ref({})
const previewDraftTab = ref('structural')
const branchStorageKey = computed(() => `inktrace:selected-branch:${projectId.value || route.params.id}`)

const latestChapterNumber = computed(() => state.generatedBatch.latestChapter?.chapter_number || novel.value?.latest_chapter_number || 0)
const latestChapterTitle = computed(() => state.generatedBatch.latestChapter?.title || novel.value?.latest_chapter_title || '暂无')
const mainPlotSummary = computed(() => (memoryView.value?.main_plot_lines || []).join('；') || '暂无')
const writingFocus = computed(() => memoryView.value?.current_progress || '暂无')
const planningReason = computed(() => state.generatedBatch.planningReason || state.previewResult.planningReason || (state.plans[0]?.planning_reason || ''))
const arcStageBefore = computed(() => state.generatedBatch.arcStageBefore || state.previewResult.arcStageBefore || (state.plans[0]?.arc_stage_before || ''))
const arcStageAfterExpected = computed(() => state.generatedBatch.arcStageAfterExpected || state.previewResult.arcStageAfterExpected || (state.plans[0]?.arc_stage_after_expected || ''))
const arcStageAfterActual = computed(() => state.generatedBatch.arcStageAfterActual || '')
const arcStageAdvanced = computed(() => Boolean(state.generatedBatch.arcStageAdvanced))
const batchStatusText = computed(() => {
  if (!state.generatedBatch.generatedChapters.length) return ''
  return state.generatedBatch.memoryRefreshed ? '保存成功，memory 已刷新' : '章节已保存，但全局摘要尚未刷新'
})
const assistantPresetText = computed(() => {
  const parts = []
  if (state.targetArcId) {
    const targetArc = (activeArcs.value || []).find((item) => item.arc_id === state.targetArcId)
    if (targetArc) {
      parts.push(`已按助手建议锁定目标弧：${targetArc.title || targetArc.arc_id}`)
    }
  }
  if (String(route.query.planningMode || '').trim()) {
    parts.push(`当前规划模式：${state.planningMode === 'deep_planning' ? '重规划' : '轻规划'}`)
  }
  return parts.join('；')
})
const normalizedGeneratedChapters = computed(() =>
  (state.generatedBatch.generatedChapters || []).map((item) => ({
    ...item,
    saved: (state.generatedBatch.savedChapterIds || []).includes(item.chapter_id)
  }))
)

const restoreSelectedBranch = () => {
  const routeSelected = String(route.query.branchId || '').trim()
  const cachedSelected = window.localStorage.getItem(branchStorageKey.value) || ''
  const candidate = routeSelected || cachedSelected
  state.selectedBranchId = candidate && state.branches.some((item) => item.id === candidate) ? candidate : (state.branches[0]?.id || '')
  if (state.selectedBranchId) {
    window.localStorage.setItem(branchStorageKey.value, state.selectedBranchId)
  }
}

const applyRouteAssistantPreset = () => {
  const queryTargetArcId = String(route.query.targetArcId || '').trim()
  const queryPlanningMode = String(route.query.planningMode || '').trim()
  if (queryTargetArcId && (activeArcs.value || []).some((item) => item.arc_id === queryTargetArcId)) {
    state.targetArcId = queryTargetArcId
  }
  if (['light_planning', 'deep_planning'].includes(queryPlanningMode)) {
    state.planningMode = queryPlanningMode
  }
}

const loadBase = async () => {
  state.loading = true
  try {
    novel.value = await novelApi.get(route.params.id)
    const project = await projectApi.getByNovel(route.params.id)
    projectId.value = project?.id || ''
    memoryView.value = projectId.value ? await projectApi.memoryViewV2(projectId.value) : {}
    const arcResult = projectId.value ? await projectApi.activePlotArcsV2(projectId.value) : {}
    activeArcs.value = arcResult?.plot_arcs || []
    const branchResult = projectId.value ? await projectApi.listBranchesV2(projectId.value) : { branches: [] }
    state.branches = branchResult?.branches || []
    restoreSelectedBranch()
    applyRouteAssistantPreset()
    state.errorMessage = ''
  } catch (error) {
    state.errorMessage = error?.message || '加载续写页失败'
  } finally {
    state.loading = false
  }
}

const generateBranches = async () => {
  if (!projectId.value) return
  state.branchLoading = true
  try {
    const result = await projectApi.branchesV2(projectId.value, { branch_count: 4 })
    state.branches = result?.branches || []
    restoreSelectedBranch()
    ElMessage.success('分支生成完成')
  } finally {
    state.branchLoading = false
  }
}

const generatePlans = async () => {
  if (!projectId.value || !state.selectedBranchId) {
    ElMessage.warning('请先生成并选择一个分支')
    return
  }
  state.planLoading = true
  try {
    const result = await projectApi.chapterPlanV2(projectId.value, {
      branch_id: state.selectedBranchId,
      chapter_count: state.chapterCount,
      target_words_per_chapter: state.targetWords,
      planning_mode: state.planningMode,
      target_arc_id: state.targetArcId || '',
      allow_deep_planning: state.planningMode === 'deep_planning'
    })
    state.plans = (result?.plans || []).map((item) => ({
      ...item,
      chapter_function_label: formatChapterFunction(item?.chapter_task_seed?.chapter_function || '')
    }))
    ElMessage.success('章节计划生成完成')
  } finally {
    state.planLoading = false
  }
}

const previewFirstPlan = async () => {
  if (!projectId.value || !state.plans.length) {
    ElMessage.warning('请先生成章节计划')
    return
  }
  state.previewLoading = true
  try {
    const firstPlan = state.plans[0]
    const result = await projectApi.writePreviewV2(projectId.value, {
      plan_id: firstPlan.id,
      target_word_count: state.targetWords,
      planning_mode: state.planningMode,
      target_arc_id: state.targetArcId || ''
    })
    state.previewResult = {
      chapterTask: result.chapter_task || null,
      structuralDraft: result.structural_draft || null,
      detemplatedDraft: result.detemplated_draft || null,
      integrityCheck: result.integrity_check || null,
      revisionAttempts: result.revision_attempts || [],
      usedStructuralFallback: Boolean(result.used_structural_fallback),
      planningReason: result.planning_reason || '',
      arcStageBefore: result.arc_stage_before || '',
      arcStageAfterExpected: result.arc_stage_after_expected || ''
    }
    previewContext.value = await projectApi.continuationContextV2(projectId.value, { chapter_number: firstPlan.chapter_number })
  } finally {
    state.previewLoading = false
  }
}

const commitBatch = async () => {
  if (!projectId.value || !state.plans.length) {
    ElMessage.warning('请先生成章节计划')
    return
  }
  state.commitLoading = true
  try {
    const planIds = state.plans.map((item) => item.id).filter(Boolean)
    if (!planIds.length) {
      ElMessage.warning('计划已失效，请重新生成章节计划后再提交')
      return
    }
    const result = await projectApi.writeCommitV2(projectId.value, {
      plan_ids: planIds,
      chapter_count: state.chapterCount,
      auto_commit: true,
      planning_mode: state.planningMode,
      target_arc_id: state.targetArcId || ''
    })
    state.generatedBatch = {
      generatedChapters: result.generated_chapters || [],
      latestChapter: result.latest_chapter || null,
      latestStructuralDraft: result.latest_structural_draft || null,
      latestDetemplatedDraft: result.latest_detemplated_draft || null,
      latestDraftIntegrityCheck: result.latest_draft_integrity_check || null,
      usedStructuralFallback: Boolean(result.used_structural_fallback),
      chapterSaved: Boolean(result.chapter_saved),
      memoryRefreshed: Boolean(result.memory_refreshed),
      savedChapterIds: result.saved_chapter_ids || [],
      planningReason: result.planning_reason || '',
      arcStageBefore: result.arc_stage_before || '',
      arcStageAfterExpected: result.arc_stage_after_expected || '',
      arcStageAfterActual: result.arc_stage_after_actual || '',
      arcStageAdvanced: Boolean(result.arc_stage_advanced)
    }
    memoryView.value = result.memory_view || memoryView.value
    await loadBase()
    ElMessage.success(state.generatedBatch.memoryRefreshed ? '保存成功，memory 已刷新' : '章节已保存，但全局摘要尚未刷新')
  } catch (error) {
    const message = error?.message || '提交失败，请先重新生成章节计划后再试'
    state.errorMessage = message
    ElMessage.warning(message)
  } finally {
    state.commitLoading = false
  }
}

const applyPreviewDraft = ({ type, mode }) => {
  const draft = type === 'detemplated' ? state.previewResult.detemplatedDraft : state.previewResult.structuralDraft
  if (!draft?.content) {
    ElMessage.warning('暂无可采纳结果')
    return
  }
  ElMessage.success(mode === 'append' ? '已准备插入正文末尾，请到章节页继续处理' : '已准备覆盖正文，请到章节页继续处理')
}

const discardPreviewDraft = () => {
  state.previewResult = {
    chapterTask: null,
    structuralDraft: null,
    detemplatedDraft: null,
    integrityCheck: null,
    revisionAttempts: [],
    usedStructuralFallback: false,
    planningReason: '',
    arcStageBefore: '',
    arcStageAfterExpected: ''
  }
}

const goToGeneratedChapter = (chapter) => {
  if (!chapter?.chapter_id) return
  router.push(`/novel/${route.params.id}/chapters/${chapter.chapter_id}/edit`)
}

const viewGeneratedChapter = (chapter) => {
  if (!chapter?.structural_draft && !chapter?.detemplated_draft) {
    ElMessage.info('当前章节缺少完整结果详情，请跳转章节编辑页查看')
    return
  }
  state.previewResult = {
    chapterTask: state.previewResult.chapterTask,
    structuralDraft: chapter.structural_draft || null,
    detemplatedDraft: chapter.detemplated_draft || null,
    integrityCheck: chapter.integrity_check || null,
    revisionAttempts: chapter.revision_attempts || [],
    usedStructuralFallback: Boolean(chapter.used_structural_fallback),
    planningReason: state.previewResult.planningReason,
    arcStageBefore: state.previewResult.arcStageBefore,
    arcStageAfterExpected: state.previewResult.arcStageAfterExpected
  }
  previewDraftTab.value = 'structural'
}

const goBack = () => {
  router.push(`/novel/${route.params.id}`)
}

onMounted(loadBase)

watch(
  () => state.selectedBranchId,
  (value) => {
    if (value) {
      window.localStorage.setItem(branchStorageKey.value, value)
    }
  }
)
</script>

<style scoped>
.novel-write-page {
  padding: 20px;
}

.section-grid {
  margin-top: 16px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.empty-text,
.branch-summary,
.branch-conflict {
  color: #606266;
}

.branch-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  width: 100%;
}

.branch-card {
  margin: 0;
  height: 100%;
  display: flex;
  align-items: stretch;
}

.branch-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

:deep(.branch-card .el-radio__label) {
  display: block;
  white-space: normal;
  width: 100%;
}

.top-gap {
  margin-top: 16px;
}
</style>
