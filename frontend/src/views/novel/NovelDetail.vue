<template>
  <div class="novel-detail-page">
    <el-page-header content="小说详情" @back="goBack" />

    <el-alert v-if="state.loading" title="正在加载小说详情与整理进度…" type="info" show-icon :closable="false" />
    <el-alert v-if="state.errorMessage" :title="state.errorMessage" type="error" show-icon :closable="false" />

    <el-row :gutter="16" class="detail-grid">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>基础信息区</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="标题">{{ state.novel?.title || '暂无' }}</el-descriptions-item>
            <el-descriptions-item label="作者">{{ state.novel?.author || '暂无' }}</el-descriptions-item>
            <el-descriptions-item label="题材">{{ formatGenre(state.novel?.genre) }}</el-descriptions-item>
            <el-descriptions-item label="简介">{{ state.novel?.description || '暂无' }}</el-descriptions-item>
            <el-descriptions-item label="章节数">{{ state.chapters.length }}</el-descriptions-item>
            <el-descriptions-item label="最新章节号">{{ latestChapterNumber }}</el-descriptions-item>
            <el-descriptions-item label="当前状态">{{ formatNovelStatus(state.novel?.status) }}</el-descriptions-item>
            <el-descriptions-item label="当前写作焦点">{{ currentWritingFocus }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>结构摘要区</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="主角/主要人物">{{ characterSummary }}</el-descriptions-item>
            <el-descriptions-item label="世界观摘要">{{ worldviewSummary }}</el-descriptions-item>
            <el-descriptions-item label="主线摘要">{{ mainPlotSummary }}</el-descriptions-item>
            <el-descriptions-item label="当前进度">{{ progressSummary }}</el-descriptions-item>
            <el-descriptions-item label="大纲摘要">{{ outlineSummary }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>当前活跃剧情弧</span>
          </template>
          <el-empty v-if="!activeArcs.length" description="暂无活跃剧情弧" />
          <template v-else>
            <el-radio-group v-model="arcTimelineType" class="top-gap">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="main_arc">主线弧</el-radio-button>
              <el-radio-button label="character_arc">人物弧</el-radio-button>
              <el-radio-button label="supporting_arc">支线弧</el-radio-button>
            </el-radio-group>
            <el-descriptions :column="1" border class="top-gap">
            <el-descriptions-item v-for="arc in filteredActiveArcs" :key="arc.arc_id" :label="arc.title || '未命名剧情弧'">
              <div>{{ formatArcType(arc.arc_type) }} · {{ formatArcStage(arc.current_stage) }}</div>
              <div>优先级：{{ formatArcPriority(arc.priority) }}</div>
              <div>{{ arc.latest_progress_summary || '暂无推进概况' }}</div>
              <div>下一步：{{ arc.next_push_suggestion || '暂无建议' }}</div>
              <div v-if="arc.latest_snapshot?.stage_before || arc.latest_snapshot?.stage_after">
                最近迁移：{{ formatArcStage(arc.latest_snapshot?.stage_before) }} -> {{ formatArcStage(arc.latest_snapshot?.stage_after) }}
              </div>
              <div v-if="arc.latest_snapshot?.change_reason">迁移原因：{{ arc.latest_snapshot?.change_reason }}</div>
                <div v-if="arc.latest_snapshot?.progress_summary">迁移证据：{{ arc.latest_snapshot?.progress_summary }}</div>
              </el-descriptions-item>
            </el-descriptions>
            <el-collapse v-if="arcTimeline.length" class="top-gap">
              <el-collapse-item title="最近迁移时间线（Active Arcs）" name="arc-timeline">
                <el-descriptions :column="1" border>
                  <el-descriptions-item v-for="item in arcTimeline" :key="item.key" :label="item.title">
                    <div>{{ formatArcStage(item.stageBefore) }} -> {{ formatArcStage(item.stageAfter) }}</div>
                    <div v-if="item.changeReason">原因：{{ item.changeReason }}</div>
                    <div v-if="item.progressSummary">证据：{{ item.progressSummary }}</div>
                    <div v-if="item.createdAt">时间：{{ item.createdAt }}</div>
                  </el-descriptions-item>
                </el-descriptions>
              </el-collapse-item>
            </el-collapse>
          </template>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>作者助手建议</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前建议">
              {{ assistantSummary }}
            </el-descriptions-item>
            <el-descriptions-item label="推荐目标弧">
              {{ recommendedArcLabel }}
            </el-descriptions-item>
            <el-descriptions-item label="推荐规划模式">
              {{ recommendedPlanningModeLabel }}
            </el-descriptions-item>
            <el-descriptions-item label="建议原因">
              {{ recommendationReason }}
            </el-descriptions-item>
            <el-descriptions-item label="执行前检查">
              {{ readinessChecklist }}
            </el-descriptions-item>
          </el-descriptions>
          <div class="action-grid top-gap">
            <el-button type="success" @click="goToWriteWithAssistant">按助手建议进入续写</el-button>
            <el-button @click="goToWrite">直接进入续写</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <span>全局操作区</span>
          </template>
          <div class="action-grid">
            <el-button @click="goToImport">导入整本小说</el-button>
            <el-button @click="goToOutlineImport">导入大纲</el-button>
            <el-button type="primary" :loading="state.organizeLoading" @click="organizeStory">整理故事结构</el-button>
            <el-button :disabled="!canPause" @click="pauseOrganize">暂停</el-button>
            <el-button :disabled="!canResume" @click="resumeOrganize">继续</el-button>
            <el-button :disabled="!canCancel" @click="cancelOrganize">取消</el-button>
            <el-button :disabled="!canRetry" @click="retryOrganize">重新整理</el-button>
            <el-button :loading="state.branchLoading" @click="generateBranches">生成分支</el-button>
            <el-button type="success" @click="goToWrite">进入续写</el-button>
            <el-button @click="state.exportDialogVisible = true">导出</el-button>
          </div>
          <div v-if="organizeProgress.status !== 'idle'" class="top-gap">
            <el-alert :title="organizeProgress.message || '整理任务进行中'" :type="organizeAlertType" show-icon :closable="false" />
            <el-descriptions :column="3" border class="top-gap">
              <el-descriptions-item label="状态">{{ formatOrganizeStatus(organizeProgress.status) }}</el-descriptions-item>
              <el-descriptions-item label="阶段">{{ organizeProgress.stage || '暂无' }}</el-descriptions-item>
              <el-descriptions-item label="进度">{{ organizeProgress.current || 0 }}/{{ organizeProgress.total || 0 }}</el-descriptions-item>
              <el-descriptions-item label="百分比">{{ organizeProgress.percent || 0 }}%</el-descriptions-item>
              <el-descriptions-item label="当前章节">{{ organizeProgress.current_chapter_title || '暂无' }}</el-descriptions-item>
              <el-descriptions-item label="说明">{{ organizeProgress.message || '暂无' }}</el-descriptions-item>
            </el-descriptions>
            <el-progress class="top-gap" :percentage="Number(organizeProgress.percent || 0)" :status="organizeProgress.status === 'error' ? 'exception' : undefined" />
          </div>
          <div v-if="state.branches.length" class="top-gap">
            <el-radio-group v-model="selectedBranchId" class="branch-list">
              <el-radio v-for="branch in state.branches" :key="branch.id" :label="branch.id" border class="branch-item">
                {{ branch.title || '未命名分支' }}
              </el-radio>
            </el-radio-group>
          </div>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>章节列表区</span>
              <div class="header-actions">
                <el-select v-model="chapterSort" size="small" style="width: 180px">
                  <el-option label="章节号从小到大" value="number_asc" />
                  <el-option label="章节号从大到小" value="number_desc" />
                  <el-option label="更新时间最新" value="updated_desc" />
                  <el-option label="更新时间最早" value="updated_asc" />
                </el-select>
                <el-button type="primary" @click="createChapter">新建章节</el-button>
                <el-button @click="importChapterEntry">导入章节</el-button>
              </div>
            </div>
          </template>
          <el-table :data="pagedChapters" border style="width: 100%">
            <el-table-column prop="number" label="章节号" width="90" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="updated_at" label="更新时间" min-width="180" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                {{ formatChapterStatus(row.status) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240">
              <template #default="{ row }">
                <el-button type="primary" link @click="editChapter(row)">编辑</el-button>
                <el-button type="primary" link @click="importChapter(row)">导入本章内容</el-button>
                <el-button type="danger" link @click="deleteChapter(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="state.chapters.length > chapterPageSize"
            class="top-gap"
            layout="total, sizes, prev, pager, next"
            :total="state.chapters.length"
            :current-page="chapterPage"
            :page-size="chapterPageSize"
            :page-sizes="[10, 20, 50, 100]"
            @update:current-page="(value) => (chapterPage.value = value)"
            @update:page-size="handlePageSizeChange"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="state.exportDialogVisible" title="导出小说" width="520px">
      <el-form label-position="top">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio label="markdown">Markdown</el-radio>
            <el-radio label="txt">TXT</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="导出范围">
          <el-radio-group v-model="exportForm.scope">
            <el-radio label="full">全文导出</el-radio>
            <el-radio label="by_chapter">按章节导出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="exportForm.scope === 'by_chapter'" label="按章节导出模式">
          <el-radio-group v-model="exportForm.chapterMode">
            <el-radio label="single">单章一个文件</el-radio>
            <el-radio label="every_10">每10章一个文件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="exportPathLabel">
          <el-input v-model="exportForm.outputPath" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="state.exportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="exportNovel">开始导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { contentApi, exportApi, novelApi, projectApi } from '@/api'
import { useNovelDetailState } from '@/composables/useNovelDetailState'
import { formatGenre, formatNovelStatus, formatOrganizeStatus } from '@/constants/display'
import { ARC_STAGE_LABELS, ARC_TYPE_LABELS } from '@/constants/storyLabels'

const route = useRoute()
const router = useRouter()
const state = useNovelDetailState()
const projectId = ref('')
const selectedBranchId = ref('')
const chapterSort = ref('number_asc')
const chapterPage = ref(1)
const chapterPageSize = ref(20)
const activeArcs = ref([])
const arcTimelineType = ref('all')
const exporting = ref(false)
const organizeProgress = ref({ status: 'idle', stage: 'idle', current: 0, total: 0, percent: 0, current_chapter_title: '', message: '' })
let progressTimer = null
let detailRefreshingAfterDone = false
const exportForm = ref({
  format: 'markdown',
  scope: 'full',
  chapterMode: 'single',
  outputPath: 'novel-export.md'
})
const exportPathLabel = computed(() => (exportForm.value.scope === 'by_chapter' ? '导出文件夹名' : '导出文件名'))

const latestChapterNumber = computed(() => {
  const latest = [...state.chapters].sort((a, b) => (b.number || 0) - (a.number || 0))[0]
  return latest?.number || 0
})
const currentWritingFocus = computed(() => state.memoryView?.current_progress || '暂无')
const characterSummary = computed(() => ((state.memoryView?.main_characters || []).map((item) => item.name).filter(Boolean).slice(0, 6).join('、') || '暂无'))
const worldviewSummary = computed(() => (state.memoryView?.world_summary || []).join('；') || '暂无')
const mainPlotSummary = computed(() => (state.memoryView?.main_plot_lines || []).join('；') || '暂无')
const progressSummary = computed(() => state.memoryView?.current_progress || '暂无')
const outlineSummary = computed(() => (state.memoryView?.outline_summary || []).join('；') || '暂无')
const sortedChapters = computed(() => {
  const chapters = [...state.chapters]
  if (chapterSort.value === 'number_desc') {
    return chapters.sort((a, b) => Number(b.number || 0) - Number(a.number || 0))
  }
  if (chapterSort.value === 'updated_desc') {
    return chapters.sort((a, b) => new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime())
  }
  if (chapterSort.value === 'updated_asc') {
    return chapters.sort((a, b) => new Date(a.updated_at || 0).getTime() - new Date(b.updated_at || 0).getTime())
  }
  return chapters.sort((a, b) => Number(a.number || 0) - Number(b.number || 0))
})
const pagedChapters = computed(() => {
  const page = Math.max(1, Number(chapterPage.value || 1))
  const size = Math.max(1, Number(chapterPageSize.value || 20))
  const start = (page - 1) * size
  return sortedChapters.value.slice(start, start + size)
})
const organizeAlertType = computed(() => {
  if (organizeProgress.value.status === 'error' || organizeProgress.value.status === 'cancelled') return 'warning'
  if (organizeProgress.value.status === 'done') return 'success'
  return 'info'
})
const canPause = computed(() => ['running', 'resume_requested'].includes(organizeProgress.value.status))
const canResume = computed(() => ['paused', 'pause_requested'].includes(organizeProgress.value.status))
const canCancel = computed(() => ['running', 'pause_requested', 'paused', 'resume_requested'].includes(organizeProgress.value.status))
const canRetry = computed(() => ['done', 'error', 'cancelled', 'paused'].includes(organizeProgress.value.status))
const formatArcType = (value) => ARC_TYPE_LABELS[value] || value || '未知'
const formatArcStage = (value) => ARC_STAGE_LABELS[value] || value || '未知'
const formatArcPriority = (value) => ({ core: '核心', major: '重要', minor: '次要' }[value] || value || '未知')
const filteredActiveArcs = computed(() => {
  if (arcTimelineType.value === 'all') return activeArcs.value || []
  return (activeArcs.value || []).filter((arc) => String(arc.arc_type || '') === arcTimelineType.value)
})
const recommendedArc = computed(() => {
  const arcs = [...(activeArcs.value || [])]
  const priorityRank = { core: 0, major: 1, minor: 2 }
  const stageRank = { crisis: 0, turning_point: 1, payoff: 2, escalation: 3, early_push: 4, setup: 5, aftermath: 6 }
  return arcs.sort((a, b) => {
    const priorityDiff = (priorityRank[a.priority] ?? 9) - (priorityRank[b.priority] ?? 9)
    if (priorityDiff !== 0) return priorityDiff
    return (stageRank[a.current_stage] ?? 9) - (stageRank[b.current_stage] ?? 9)
  })[0] || null
})
const recommendedArcLabel = computed(() => {
  if (!recommendedArc.value) return '暂无可推荐剧情弧'
  return `${recommendedArc.value.title || recommendedArc.value.arc_id} · ${formatArcType(recommendedArc.value.arc_type)} · ${formatArcStage(recommendedArc.value.current_stage)}`
})
const recommendedPlanningMode = computed(() => {
  const stage = String(recommendedArc.value?.current_stage || '')
  return ['crisis', 'turning_point', 'payoff'].includes(stage) ? 'deep_planning' : 'light_planning'
})
const recommendedPlanningModeLabel = computed(() => (recommendedPlanningMode.value === 'deep_planning' ? '重规划' : '轻规划'))
const recommendationReason = computed(() => {
  if (!recommendedArc.value) {
    return organizeProgress.value.status === 'done' ? '当前缺少活跃剧情弧，建议先重新整理或补充结构信息。' : '等待整理完成后再生成剧情弧建议。'
  }
  return recommendedArc.value.latest_snapshot?.change_reason || recommendedArc.value.stage_reason || recommendedArc.value.next_push_suggestion || '建议优先推进当前最关键的活跃剧情弧。'
})
const readinessChecklist = computed(() => {
  const checks = []
  checks.push(projectId.value ? '已绑定项目' : '缺少项目')
  checks.push(activeArcs.value.length ? `活跃弧 ${activeArcs.value.length} 条` : '暂无活跃弧')
  checks.push(state.branches.length ? `已生成分支 ${state.branches.length} 个` : '尚未生成分支')
  return checks.join('；')
})
const assistantSummary = computed(() => {
  if (!projectId.value) return '当前小说还没有绑定项目，建议先完成导入与整理。'
  if (organizeProgress.value.status !== 'done') return '建议先完成全书整理，再根据剧情弧进入续写。'
  if (!recommendedArc.value) return '剧情弧已接通，但当前没有明确推荐弧，建议重新整理或刷新记忆。'
  return `优先推进“${recommendedArc.value.title || recommendedArc.value.arc_id}”，并使用${recommendedPlanningModeLabel.value}生成下一章计划。`
})
const arcTimeline = computed(() =>
  (filteredActiveArcs.value || [])
    .map((arc) => ({
      key: `${arc.arc_id}:${arc.latest_snapshot?.snapshot_id || ''}`,
      title: arc.title || arc.arc_id || '未命名剧情弧',
      stageBefore: arc.latest_snapshot?.stage_before || '',
      stageAfter: arc.latest_snapshot?.stage_after || '',
      changeReason: arc.latest_snapshot?.change_reason || '',
      progressSummary: arc.latest_snapshot?.progress_summary || '',
      createdAt: arc.latest_snapshot?.created_at || ''
    }))
    .filter((item) => item.stageBefore || item.stageAfter || item.progressSummary)
)
const branchStorageKey = computed(() => `inktrace:selected-branch:${projectId.value || route.params.id}`)
const arcTimelineTypeStorageKey = computed(() => `inktrace:arc-type:${route.params.id || projectId.value || 'unknown'}`)
const chapterSortStorageKey = computed(() => `inktrace:chapter-sort:${route.params.id || projectId.value || 'unknown'}`)
const chapterPageSizeStorageKey = computed(() => `inktrace:chapter-page-size:${route.params.id || projectId.value || 'unknown'}`)

const stopProgressPolling = () => {
  if (progressTimer) {
    window.clearTimeout(progressTimer)
    progressTimer = null
  }
}

const withTimeout = async (promise, fallbackValue, timeoutMs = 8000) => {
  let timer = null
  try {
    return await Promise.race([
      promise,
      new Promise((resolve) => {
        timer = window.setTimeout(() => resolve(fallbackValue), timeoutMs)
      })
    ])
  } finally {
    if (timer) window.clearTimeout(timer)
  }
}

const fetchOrganizeProgress = async () => {
  if (!route.params.id) return
  organizeProgress.value = await withTimeout(contentApi.organizeProgress(route.params.id), organizeProgress.value, 5000)
  if (['running', 'pause_requested', 'resume_requested', 'cancelling'].includes(organizeProgress.value.status)) {
    stopProgressPolling()
    progressTimer = window.setTimeout(fetchOrganizeProgress, 1200)
  } else {
    stopProgressPolling()
    if (organizeProgress.value.status === 'done' && projectId.value && !detailRefreshingAfterDone) {
      detailRefreshingAfterDone = true
      state.memoryView = await withTimeout(projectApi.memoryViewV2(projectId.value), state.memoryView || {}, 5000)
      state.novel = await withTimeout(novelApi.get(route.params.id), state.novel || {}, 5000)
      state.chapters = state.novel?.chapters || []
      await loadActiveArcs()
      await loadPersistedBranches()
    }
  }
}

const loadPersistedBranches = async () => {
  if (!projectId.value) return
  const result = await withTimeout(projectApi.listBranchesV2(projectId.value), { branches: [] }, 5000)
  state.branches = result?.branches || []
  const saved = window.localStorage.getItem(branchStorageKey.value)
  selectedBranchId.value = saved && state.branches.some((item) => item.id === saved) ? saved : ''
}

const loadActiveArcs = async () => {
  if (!projectId.value) {
    activeArcs.value = []
    return
  }
  const result = await withTimeout(projectApi.activePlotArcsV2(projectId.value), { plot_arcs: [] }, 5000)
  activeArcs.value = result?.plot_arcs || []
}

const loadArcTimelineTypePreference = () => {
  const saved =
    window.localStorage.getItem(arcTimelineTypeStorageKey.value) ||
    window.localStorage.getItem(`inktrace:arc-timeline-type:${projectId.value || route.params.id}`) ||
    'all'
  arcTimelineType.value = ['all', 'main_arc', 'character_arc', 'supporting_arc'].includes(saved) ? saved : 'all'
}

const loadChapterSortPreference = () => {
  const saved = window.localStorage.getItem(chapterSortStorageKey.value) || 'number_asc'
  chapterSort.value = ['number_asc', 'number_desc', 'updated_desc', 'updated_asc'].includes(saved) ? saved : 'number_asc'
}

const loadChapterPageSizePreference = () => {
  const raw = Number(window.localStorage.getItem(chapterPageSizeStorageKey.value) || 20)
  chapterPageSize.value = [10, 20, 50, 100].includes(raw) ? raw : 20
}

const handlePageSizeChange = (value) => {
  chapterPageSize.value = Number(value || 20)
  chapterPage.value = 1
}

const loadPage = async () => {
  state.loading = true
  try {
    state.novel = await withTimeout(novelApi.get(route.params.id), state.novel || {}, 8000)
    state.chapters = state.novel?.chapters || []
    const project = await withTimeout(projectApi.getByNovel(route.params.id), {}, 6000)
    projectId.value = project?.id || ''
    state.memoryView = projectId.value ? await withTimeout(projectApi.memoryViewV2(projectId.value), state.memoryView || {}, 6000) : {}
    await loadActiveArcs()
    loadArcTimelineTypePreference()
    loadChapterSortPreference()
    loadChapterPageSizePreference()
    await loadPersistedBranches()
    fetchOrganizeProgress()
    if (organizeProgress.value.status !== 'done') {
      detailRefreshingAfterDone = false
    }
    state.errorMessage = ''
  } catch (error) {
    state.errorMessage = error?.message || '加载详情页失败'
  } finally {
    state.loading = false
  }
}

const organizeStory = async () => {
  if (!route.params.id) return
  state.organizeLoading = true
  try {
    await contentApi.startOrganize(route.params.id, false)
    await fetchOrganizeProgress()
    ElMessage.success('整理任务已启动')
  } finally {
    state.organizeLoading = false
  }
}

const pauseOrganize = async () => {
  await contentApi.pauseOrganize(route.params.id)
  await fetchOrganizeProgress()
  ElMessage.success('已请求暂停整理')
}

const resumeOrganize = async () => {
  await contentApi.resumeOrganize(route.params.id)
  await fetchOrganizeProgress()
  ElMessage.success('已请求继续整理')
}

const cancelOrganize = async () => {
  await contentApi.cancelOrganize(route.params.id)
  await fetchOrganizeProgress()
  ElMessage.success('已请求取消整理')
}

const retryOrganize = async () => {
  await contentApi.retryOrganize(route.params.id)
  await fetchOrganizeProgress()
  ElMessage.success('已重新开始整理')
}

const generateBranches = async () => {
  if (!projectId.value) return
  state.branchLoading = true
  try {
    const result = await projectApi.branchesV2(projectId.value, { branch_count: 4 })
    state.branches = result?.branches || []
    selectedBranchId.value = state.branches[0]?.id || ''
    if (selectedBranchId.value) window.localStorage.setItem(branchStorageKey.value, selectedBranchId.value)
    ElMessage.success('分支生成完成')
  } finally {
    state.branchLoading = false
  }
}

const createChapter = () => {
  router.push(`/novel/${route.params.id}/chapters/new`)
}

const editChapter = (chapter) => {
  router.push(`/novel/${route.params.id}/chapters/${chapter.id}/edit`)
}

const importChapter = (chapter) => {
  router.push(`/novel/${route.params.id}/chapters/${chapter.id}/edit`)
}

const importChapterEntry = () => {
  ElMessage.info('请进入章节编辑页后执行具体单章导入')
}

const deleteChapter = async (chapter) => {
  await ElMessageBox.confirm(`确认删除《${chapter.title || `第${chapter.number}章`}》吗？`, '删除章节', { type: 'warning' })
  await novelApi.deleteChapter(route.params.id, chapter.id)
  ElMessage.success('章节已删除')
  await loadPage()
}

const goToWrite = () => {
  if (selectedBranchId.value) {
    window.localStorage.setItem(branchStorageKey.value, selectedBranchId.value)
  }
  router.push({ path: `/novel/${route.params.id}/write`, query: selectedBranchId.value ? { branchId: selectedBranchId.value } : {} })
}

const goToWriteWithAssistant = () => {
  if (selectedBranchId.value) {
    window.localStorage.setItem(branchStorageKey.value, selectedBranchId.value)
  }
  const query = {}
  if (selectedBranchId.value) query.branchId = selectedBranchId.value
  if (recommendedArc.value?.arc_id) query.targetArcId = recommendedArc.value.arc_id
  if (recommendedPlanningMode.value) query.planningMode = recommendedPlanningMode.value
  router.push({ path: `/novel/${route.params.id}/write`, query })
}

const goToImport = () => {
  router.push('/import')
}

const goToOutlineImport = () => {
  router.push('/import')
  ElMessage.info('请在导入页填写大纲文件路径后继续导入')
}

const exportNovel = async () => {
  exporting.value = true
  try {
    const result = await exportApi.export({
      novel_id: route.params.id,
      output_path: exportForm.value.outputPath,
      format: exportForm.value.format,
      scope: exportForm.value.scope,
      options: {
        chapter_export_mode: exportForm.value.chapterMode
      }
    })
    state.exportDialogVisible = false
    if (result?.file_path) {
      window.open(exportApi.download(result.file_path), '_blank')
    }
    ElMessage.success('导出任务已完成')
  } finally {
    exporting.value = false
  }
}

const goBack = () => {
  router.push('/projects')
}

const refreshExportOutputPath = () => {
  const novelTitle = state.novel?.title || 'novel-export'
  if (exportForm.value.scope === 'by_chapter') {
    exportForm.value.outputPath = novelTitle
    return
  }
  const suffix = exportForm.value.format === 'txt' ? 'txt' : 'md'
  exportForm.value.outputPath = `${novelTitle}.${suffix}`
}

onMounted(loadPage)
onBeforeUnmount(stopProgressPolling)

watch(selectedBranchId, (value) => {
  if (value && branchStorageKey.value) {
    window.localStorage.setItem(branchStorageKey.value, value)
  }
})

watch(arcTimelineType, (value) => {
  if (arcTimelineTypeStorageKey.value) {
    window.localStorage.setItem(arcTimelineTypeStorageKey.value, value || 'all')
  }
})

watch(chapterSort, (value) => {
  if (chapterSortStorageKey.value) {
    window.localStorage.setItem(chapterSortStorageKey.value, value || 'number_asc')
  }
  chapterPage.value = 1
})

watch(chapterPageSize, (value) => {
  if (chapterPageSizeStorageKey.value) {
    window.localStorage.setItem(chapterPageSizeStorageKey.value, String(value || 20))
  }
})

watch(
  () => state.chapters.length,
  (length) => {
    const maxPage = Math.max(1, Math.ceil(Number(length || 0) / Number(chapterPageSize.value || 20)))
    if (chapterPage.value > maxPage) {
      chapterPage.value = maxPage
    }
  }
)

watch(
  () => [exportForm.value.scope, exportForm.value.format, state.novel?.title],
  refreshExportOutputPath,
  { immediate: true }
)
</script>

<style scoped>
.novel-detail-page {
  padding: 20px;
}

.detail-grid {
  margin-top: 16px;
}

.action-grid,
.header-row,
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.header-row {
  justify-content: space-between;
}

.top-gap {
  margin-top: 12px;
}

.branch-list {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.branch-item {
  margin: 0;
}
</style>
