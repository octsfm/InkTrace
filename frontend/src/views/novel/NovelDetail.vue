<template>
  <div class="novel-detail-page">
    <el-page-header content="小说详情" @back="goBack" />

    <el-alert v-if="state.loading" title="正在加载小说详情…" type="info" show-icon :closable="false" />
    <el-alert v-else-if="state.backgroundLoading" title="正在补充结构记忆与剧情弧信息…" type="info" show-icon :closable="false" />
    <el-alert v-if="state.errorMessage" :title="state.errorMessage" type="error" show-icon :closable="false" />

    <el-row :gutter="16" class="detail-grid">
      <el-col :xs="24" :lg="15">
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
          <el-descriptions :column="1" border>
            <el-descriptions-item label="全书总弧">
              {{ wholeBookArcSummary }}
            </el-descriptions-item>
            <el-descriptions-item label="开局至今">
              {{ openingToNowArcSummary }}
            </el-descriptions-item>
            <el-descriptions-item label="最近几章">
              {{ recentChapterArcSummary }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-if="!activeArcs.length" description="暂无活跃剧情弧" />
          <template v-else>
            <el-radio-group v-model="arcTimelineType" class="top-gap">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="main_arc">主线弧</el-radio-button>
              <el-radio-button label="character_arc">人物弧</el-radio-button>
              <el-radio-button label="supporting_arc">支线弧</el-radio-button>
            </el-radio-group>
            <el-descriptions :column="1" border class="top-gap">
            <el-descriptions-item v-for="arc in filteredActiveArcs" :key="arc.arc_id" :label="arc.display_title || arc.title || '未命名剧情弧'">
              <div>{{ formatArcType(arc.arc_type) }} · {{ formatArcStage(arc.current_stage) }}</div>
              <div>优先级：{{ formatArcPriority(arc.priority) }}</div>
              <div v-if="arc.covered_chapter_count">覆盖章节：{{ arc.covered_chapter_count }} 章</div>
              <div>{{ arc.display_summary || '暂无推进概况' }}</div>
              <div>下一步：{{ arc.display_next_push || '暂无建议' }}</div>
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

      <el-col :xs="24" :lg="9">
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
            <el-button :disabled="!canRetry" :loading="state.organizeLoading" @click="retryOrganize">重新整理</el-button>
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
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
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
const organizeProgress = ref({ status: 'idle', stage: 'idle', current: 0, total: 0, percent: 0, current_chapter_title: '', message: '', last_error: '' })
let progressTimer = null
let supplementalLoadTimer = null
let deepSupplementalLoadTimer = null
let detailRefreshingAfterDone = false
let latestLoadToken = 0
const pendingRequestControllers = new Set()
const lastOrganizeNoticeKey = ref('')
const activeOrganizeStatuses = ['running', 'pause_requested', 'resume_requested', 'cancelling']
const terminalOrganizeStatuses = ['paused', 'cancelled', 'error', 'done']
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
const FALLBACK_ARC_TITLE_RE = /main story arc|character arc|supporting pressure arc|supporting world arc/i
const FALLBACK_REASON_RE = /fallback_|supplemented_|default_light_planning|default_deep_planning/i
const splitStoryText = (value) => String(value || '')
  .replace(/\s+/g, ' ')
  .split(/[；;。！？!\n]/)
  .map((item) => item.trim())
  .filter(Boolean)
const isOutlineEcho = (value) => String(value || '').trim().length > 120
const isLowValueArcText = (value) => {
  const text = String(value || '').trim()
  if (!text) return true
  if (FALLBACK_ARC_TITLE_RE.test(text)) return true
  if (FALLBACK_REASON_RE.test(text)) return true
  if (/^(题材|前期|后期|世界背景|故事背景|主人公的修仙背景|预计字数)/.test(text)) return true
  if (/^(main_arc|character_arc|supporting_arc|light_planning|deep_planning)$/i.test(text)) return true
  return false
}
const compactStoryText = (value, fallback = '暂无') => {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  if (!text) return fallback
  if (text.length <= 56) return text
  return `${text.slice(0, 56)}...`
}
const parseChapterSummary = (value) => {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  if (!text) return null
  const match = text.match(/^([^：:]+)[：:]\s*(.+)$/)
  if (!match) {
    return { title: '', summary: text }
  }
  return {
    title: String(match[1] || '').trim(),
    summary: String(match[2] || '').trim()
  }
}
const pickMeaningfulStoryLines = (items, limit = 3) => {
  const results = []
  for (const item of items || []) {
    for (const part of splitStoryText(item)) {
      if (isLowValueArcText(part) || isOutlineEcho(part)) continue
      if (!results.includes(part)) {
        results.push(part)
      }
      if (results.length >= limit) {
        return results
      }
    }
  }
  return results
}
const parsedChapterSummaries = computed(() =>
  (state.memory?.chapter_summaries || [])
    .map(parseChapterSummary)
    .filter(Boolean)
)
const currentWritingFocus = computed(() => state.memoryView?.current_progress || '暂无')
const characterSummary = computed(() => ((state.memoryView?.main_characters || []).map((item) => item.name).filter(Boolean).slice(0, 6).join('、') || '暂无'))
const worldviewSummary = computed(() => (state.memoryView?.world_summary || []).join('；') || '暂无')
const mainPlotSummary = computed(() => {
  const lines = pickMeaningfulStoryLines(state.memoryView?.main_plot_lines || [], 3)
  if (lines.length) {
    return lines.join('；')
  }
  return compactStoryText(state.memoryView?.current_progress || '')
})
const progressSummary = computed(() => state.memoryView?.current_progress || '暂无')
const outlineSummary = computed(() => {
  const lines = pickMeaningfulStoryLines(state.memoryView?.outline_summary || [], 2)
  if (lines.length) {
    return lines.join('；')
  }
  return '暂无'
})
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
const organizeTerminalMessage = computed(() => (
  organizeProgress.value.last_error ||
  organizeProgress.value.message ||
  ''
))
const canPause = computed(() => ['running', 'resume_requested'].includes(organizeProgress.value.status))
const canResume = computed(() => ['paused', 'pause_requested'].includes(organizeProgress.value.status))
const canCancel = computed(() => ['running', 'pause_requested', 'paused', 'resume_requested'].includes(organizeProgress.value.status))
const canRetry = computed(() => ['done', 'error', 'cancelled', 'paused'].includes(organizeProgress.value.status))
const notifyOrganizeTerminalStatus = () => {
  const status = String(organizeProgress.value.status || '')
  const message = organizeTerminalMessage.value
  if (!terminalOrganizeStatuses.includes(status) || !message) return
  const noticeKey = `${status}:${message}`
  if (lastOrganizeNoticeKey.value === noticeKey) return
  lastOrganizeNoticeKey.value = noticeKey
  if (status === 'error') {
    ElMessage.error(message)
    return
  }
  if (status === 'done') return
  ElMessage.warning(message)
}
const formatArcType = (value) => ARC_TYPE_LABELS[value] || value || '未知'
const formatArcStage = (value) => ARC_STAGE_LABELS[value] || value || '未知'
const formatArcPriority = (value) => ({ core: '核心', major: '重要', minor: '次要' }[value] || value || '未知')
const buildArcDisplayTitle = (arc) => {
  const rawTitle = String(arc?.title || '').trim()
  if (rawTitle && !FALLBACK_ARC_TITLE_RE.test(rawTitle)) {
    return rawTitle
  }
  if (arc?.arc_type === 'main_arc') return '主线推进弧'
  if (arc?.arc_type === 'character_arc') return '人物成长弧'
  return '支线压力弧'
}
const buildArcDisplaySummary = (arc) => {
  const candidates = [
    arc?.latest_snapshot?.progress_summary,
    arc?.latest_progress_summary,
    state.memory?.current_state?.latest_summary,
    arc?.arc_type === 'main_arc' ? wholeBookArcSummary.value : '',
    arc?.arc_type === 'character_arc' ? openingToNowArcSummary.value : '',
    arc?.arc_type === 'supporting_arc' ? recentChapterArcSummary.value : '',
    state.memoryView?.current_progress,
    ...(state.memoryView?.main_plot_lines || [])
  ]
  const picked = pickMeaningfulStoryLines(candidates, 1)[0]
  return picked || compactStoryText(candidates.find((item) => String(item || '').trim()), '暂无推进概况')
}
const buildArcDisplayNextPush = (arc) => {
  const candidates = [
    arc?.latest_snapshot?.change_reason,
    state.memory?.current_state?.next_writing_focus,
    arc?.next_push_suggestion,
    state.memoryView?.current_progress,
    ...(state.memoryView?.main_plot_lines || [])
  ]
  const picked = pickMeaningfulStoryLines(candidates, 1)[0]
  if (picked) {
    return compactStoryText(picked, '暂无建议')
  }
  if (arc?.arc_type === 'main_arc') return '继续推进当前主线冲突'
  if (arc?.arc_type === 'character_arc') return '继续施加人物选择与代价'
  return '让支线因素重新影响主线'
}
const normalizeArcForDisplay = (arc) => ({
  ...arc,
  display_title: buildArcDisplayTitle(arc),
  display_summary: buildArcDisplaySummary(arc),
  display_next_push: buildArcDisplayNextPush(arc),
})
const filteredActiveArcs = computed(() => {
  const arcs = (activeArcs.value || []).map(normalizeArcForDisplay)
  if (arcTimelineType.value === 'all') return arcs
  return arcs.filter((arc) => String(arc.arc_type || '') === arcTimelineType.value)
})
const recommendedArc = computed(() => {
  const arcs = [...(activeArcs.value || []).map(normalizeArcForDisplay)]
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
  return `${recommendedArc.value.display_title || recommendedArc.value.title || recommendedArc.value.arc_id} · ${formatArcType(recommendedArc.value.arc_type)} · ${formatArcStage(recommendedArc.value.current_stage)}`
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
  const snapshotReason = compactStoryText(recommendedArc.value.latest_snapshot?.change_reason || '', '')
  if (snapshotReason && !isLowValueArcText(snapshotReason)) {
    return snapshotReason
  }
  return `当前最新推进集中在“${recommendedArc.value.display_summary || '该剧情弧'}”，这条弧优先级更高，适合先继续推进。`
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
  return `优先推进“${recommendedArc.value.display_title || recommendedArc.value.title || recommendedArc.value.arc_id}”，下一章先处理“${recommendedArc.value.display_next_push || '当前冲突'}”，并使用${recommendedPlanningModeLabel.value}生成计划。`
})
const recentChapterArcSummary = computed(() => {
  const recentAnalyses = (state.memory?.chapter_analysis_memories || [])
    .filter((item) => item && (item.summary || item.chapter_title))
    .slice(-3)
  if (recentAnalyses.length) {
    return recentAnalyses
      .map((item) => {
        const title = String(item.chapter_title || `第${item.chapter_number || '?'}章`).trim()
        const summary = compactStoryText(item.summary || item.conflict || item.plot_role || '', '')
        return summary ? `${title}：${summary}` : title
      })
      .join('；')
  }
  const recentSummaryItems = parsedChapterSummaries.value.slice(-3)
  if (recentSummaryItems.length) {
    return recentSummaryItems
      .map((item, index) => {
        const title = item.title || `最近第${index + 1}段`
        const summary = compactStoryText(item.summary || '', '')
        return summary ? `${title}：${summary}` : title
      })
      .join('；')
  }
  const recentChapters = [...(state.chapters || [])].sort((a, b) => Number(a.number || 0) - Number(b.number || 0)).slice(-3)
  if (recentChapters.length) {
    return recentChapters.map((item) => `第${item.number}章《${item.title || '未命名'}》`).join('；')
  }
  return '暂无'
})
const wholeBookArcSummary = computed(() => {
  const firstSummary = compactStoryText(parsedChapterSummaries.value[0]?.summary || '', '')
  const latestSummary = compactStoryText(state.memory?.current_state?.latest_summary || parsedChapterSummaries.value.at(-1)?.summary || '', '')
  if (firstSummary && latestSummary && firstSummary !== latestSummary) {
    return `从${firstSummary}起步，目前推进到${latestSummary}`
  }
  const candidates = [
    state.memory?.global_constraints?.main_plot,
    state.memory?.outline_context?.premise,
    parsedChapterSummaries.value[0]?.summary,
    parsedChapterSummaries.value[1]?.summary,
    ...(state.memoryView?.outline_summary || []),
    ...(state.memoryView?.main_plot_lines || []),
  ]
  const picked = pickMeaningfulStoryLines(candidates, 2)
  if (picked.length) {
    return picked.join('；')
  }
  return '暂无'
})
const openingToNowArcSummary = computed(() => {
  const firstSummary = compactStoryText(parsedChapterSummaries.value[0]?.summary || '', '')
  const latestSummary = compactStoryText(state.memory?.current_state?.latest_summary || state.memoryView?.current_progress || '', '')
  if (firstSummary && latestSummary && firstSummary !== latestSummary) {
    return `从开局的${firstSummary}，一路推进到现在的${latestSummary}`
  }
  const candidates = [
    recommendedArc.value?.display_summary,
    state.memory?.current_state?.latest_summary,
    state.memory?.current_state?.next_writing_focus,
    state.memoryView?.current_progress,
    ...(state.memoryView?.main_plot_lines || []),
  ]
  const picked = pickMeaningfulStoryLines(candidates, 2)
  if (picked.length) {
    return picked.join('；')
  }
  return '暂无'
})
const arcTimeline = computed(() =>
  (filteredActiveArcs.value || [])
    .map((arc) => ({
      key: `${arc.arc_id}:${arc.latest_snapshot?.snapshot_id || ''}`,
      title: arc.display_title || arc.title || arc.arc_id || '未命名剧情弧',
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

const stopSupplementalLoad = () => {
  if (supplementalLoadTimer) {
    window.clearTimeout(supplementalLoadTimer)
    supplementalLoadTimer = null
  }
}

const stopDeepSupplementalLoad = () => {
  if (deepSupplementalLoadTimer) {
    window.clearTimeout(deepSupplementalLoadTimer)
    deepSupplementalLoadTimer = null
  }
}

const isCanceledError = (error) => (
  error?.code === 'ERR_CANCELED' ||
  error?.name === 'CanceledError'
)

const cancelPendingWork = () => {
  latestLoadToken = Date.now()
  stopProgressPolling()
  stopSupplementalLoad()
  stopDeepSupplementalLoad()
  pendingRequestControllers.forEach((controller) => controller.abort())
  pendingRequestControllers.clear()
  state.loading = false
  state.backgroundLoading = false
}

const ACTION_TIMEOUT_FALLBACK = Object.freeze({ __timeout: true })

const withTimeout = async (promise, fallbackValue, timeoutMs = 8000, onTimeout = null) => {
  let timer = null
  try {
    return await Promise.race([
      promise,
      new Promise((resolve) => {
        timer = window.setTimeout(() => {
          if (typeof onTimeout === 'function') onTimeout()
          resolve(fallbackValue)
        }, timeoutMs)
      })
    ])
  } finally {
    if (timer) window.clearTimeout(timer)
  }
}

const runAbortableRequest = async (requestFactory, fallbackValue, timeoutMs = 8000) => {
  const controller = new AbortController()
  pendingRequestControllers.add(controller)
  try {
    return await withTimeout(requestFactory({ signal: controller.signal }), fallbackValue, timeoutMs, () => controller.abort())
  } finally {
    pendingRequestControllers.delete(controller)
  }
}

const withActionTimeout = async (promise, timeoutMs = 8000, message = '操作超时，请稍后重试。') => {
  const result = await withTimeout(promise, ACTION_TIMEOUT_FALLBACK, timeoutMs)
  if (result === ACTION_TIMEOUT_FALLBACK) {
    throw new Error(message)
  }
  return result
}

const unwrapSettledValue = (result, fallbackValue) => (
  result?.status === 'fulfilled' ? result.value : fallbackValue
)

const collectSettledErrors = (results) => results
  .filter((item) => item?.status === 'rejected' && !isCanceledError(item.reason))
  .map((item) => item.reason)

const applyOrganizeProgress = async (progress, options = {}) => {
  const { refreshAfterDone = true, notifyTerminal = true } = options
  organizeProgress.value = progress || organizeProgress.value
  if (activeOrganizeStatuses.includes(organizeProgress.value.status)) {
    lastOrganizeNoticeKey.value = ''
    stopProgressPolling()
    progressTimer = window.setTimeout(fetchOrganizeProgress, 1200)
    return
  }
  stopProgressPolling()
  if (notifyTerminal) {
    notifyOrganizeTerminalStatus()
  }
  if (refreshAfterDone && organizeProgress.value.status === 'done' && projectId.value && !detailRefreshingAfterDone) {
    detailRefreshingAfterDone = true
    const results = await Promise.allSettled([
      runAbortableRequest((config) => projectApi.memoryV2(projectId.value, config), state.memory || {}, 6000),
      runAbortableRequest((config) => projectApi.memoryViewV2(projectId.value, config), state.memoryView || {}, 5000),
      runAbortableRequest((config) => novelApi.get(route.params.id, config), state.novel || {}, 5000),
      loadNovelChapters(),
      runAbortableRequest((config) => projectApi.activePlotArcsV2(projectId.value, config), { plot_arcs: [] }, 5000),
      runAbortableRequest((config) => projectApi.listBranchesV2(projectId.value, config), { branches: [] }, 5000)
    ])
    const [memoryResult, memoryViewResult, novelResult, chaptersResult, activeArcResult, branchesResult] = results
    const errors = collectSettledErrors(results)
    state.memory = unwrapSettledValue(memoryResult, state.memory || {}) || {}
    state.memoryView = unwrapSettledValue(memoryViewResult, state.memoryView || {}) || {}
    state.novel = unwrapSettledValue(novelResult, state.novel || {}) || {}
    const chapters = unwrapSettledValue(chaptersResult, state.chapters || [])
    state.chapters = Array.isArray(chapters) && chapters.length ? chapters : (Array.isArray(state.chapters) ? state.chapters : [])
    activeArcs.value = unwrapSettledValue(activeArcResult, { plot_arcs: activeArcs.value || [] })?.plot_arcs || []
    state.branches = unwrapSettledValue(branchesResult, { branches: state.branches || [] })?.branches || []
    const saved = window.localStorage.getItem(branchStorageKey.value)
    selectedBranchId.value = saved && state.branches.some((item) => item.id === saved) ? saved : ''
    if (errors.length && !state.errorMessage) {
      state.errorMessage = errors[0]?.message || '整理完成后的补充信息部分加载失败'
    }
  }
}

const fetchOrganizeProgress = async () => {
  if (!route.params.id) return
  try {
    const progress = await runAbortableRequest(
      (config) => contentApi.organizeProgress(route.params.id, config),
      organizeProgress.value,
      5000
    )
    await applyOrganizeProgress(progress)
  } catch (error) {
    if (isCanceledError(error)) return
    stopProgressPolling()
    state.errorMessage = error?.message || '读取整理进度失败'
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

const loadNovelChapters = async () => {
  try {
    const chapters = await runAbortableRequest(
      (config) => novelApi.listChapters(route.params.id, config),
      state.chapters || [],
      8000
    )
    return Array.isArray(chapters) ? chapters : []
  } catch (error) {
    if (isCanceledError(error)) return []
    return Array.isArray(state.novel?.chapters) ? state.novel.chapters : (Array.isArray(state.chapters) ? state.chapters : [])
  }
}

const loadDeepSupplementalData = async (token) => {
  if (!projectId.value) return
  try {
    const results = await Promise.allSettled([
      runAbortableRequest((config) => projectApi.memoryV2(projectId.value, config), state.memory || {}, 7000),
      runAbortableRequest((config) => projectApi.listBranchesV2(projectId.value, config), { branches: [] }, 5000)
    ])
    if (token !== latestLoadToken) return
    const [memoryResult, branchesResult] = results
    state.memory = unwrapSettledValue(memoryResult, state.memory || {}) || {}
    state.branches = unwrapSettledValue(branchesResult, { branches: state.branches || [] })?.branches || []
    const saved = window.localStorage.getItem(branchStorageKey.value)
    selectedBranchId.value = saved && state.branches.some((item) => item.id === saved) ? saved : ''
  } catch (error) {
    if (token !== latestLoadToken || isCanceledError(error)) return
    if (!state.errorMessage) {
      state.errorMessage = error?.message || '加载补充记忆信息失败'
    }
  }
}

const loadSupplementalData = async (token) => {
  if (!projectId.value) {
    state.memory = {}
    state.memoryView = {}
    activeArcs.value = []
    state.branches = []
    fetchOrganizeProgress()
    return
  }

  state.backgroundLoading = true
  try {
    const results = await Promise.allSettled([
      runAbortableRequest((config) => projectApi.memoryViewV2(projectId.value, config), state.memoryView || {}, 6000),
      runAbortableRequest((config) => projectApi.activePlotArcsV2(projectId.value, config), { plot_arcs: [] }, 5000),
      runAbortableRequest((config) => contentApi.organizeProgress(route.params.id, config), organizeProgress.value, 5000)
    ])
    if (token !== latestLoadToken) return
    const [memoryViewResult, activeArcResult, progressResult] = results
    const errors = collectSettledErrors(results)
    state.memoryView = unwrapSettledValue(memoryViewResult, state.memoryView || {}) || {}
    activeArcs.value = unwrapSettledValue(activeArcResult, { plot_arcs: activeArcs.value || [] })?.plot_arcs || []
    await applyOrganizeProgress(unwrapSettledValue(progressResult, organizeProgress.value), { refreshAfterDone: false, notifyTerminal: false })
    if (organizeProgress.value.status !== 'done') {
      detailRefreshingAfterDone = false
    }
    if (errors.length && !state.errorMessage) {
      state.errorMessage = errors[0]?.message || '加载结构信息失败'
    }
  } finally {
    if (token === latestLoadToken) {
      state.backgroundLoading = false
    }
  }
}

const loadPage = async () => {
  const token = Date.now()
  latestLoadToken = token
  state.loading = true
  state.backgroundLoading = false
  try {
    const results = await Promise.allSettled([
      runAbortableRequest((config) => novelApi.get(route.params.id, config), state.novel || {}, 8000),
      loadNovelChapters(),
      runAbortableRequest((config) => projectApi.getByNovel(route.params.id, config), {}, 6000)
    ])
    if (token !== latestLoadToken) return
    const [novelResult, chaptersResult, projectResult] = results
    const errors = collectSettledErrors(results)
    state.novel = unwrapSettledValue(novelResult, state.novel || {}) || {}
    const chapters = unwrapSettledValue(chaptersResult, state.chapters || [])
    state.chapters = Array.isArray(chapters) && chapters.length ? chapters : (Array.isArray(state.chapters) ? state.chapters : [])
    projectId.value = unwrapSettledValue(projectResult, {})?.id || ''
    loadArcTimelineTypePreference()
    loadChapterSortPreference()
    loadChapterPageSizePreference()
    state.errorMessage = state.novel?.id || state.chapters.length ? '' : (errors[0]?.message || '加载详情页失败')
  } finally {
    if (token === latestLoadToken) {
      state.loading = false
    }
  }
  if (token === latestLoadToken) {
    stopSupplementalLoad()
    supplementalLoadTimer = window.setTimeout(() => {
      supplementalLoadTimer = null
      if (token === latestLoadToken) {
        void loadSupplementalData(token)
      }
    }, 0)
    stopDeepSupplementalLoad()
    deepSupplementalLoadTimer = window.setTimeout(() => {
      deepSupplementalLoadTimer = null
      if (token === latestLoadToken) {
        void loadDeepSupplementalData(token)
      }
    }, 400)
  }
}

const organizeStory = async () => {
  if (!route.params.id) return
  state.organizeLoading = true
  try {
    await withActionTimeout(contentApi.startOrganize(route.params.id, false, 'full_reanalyze'), 8000, '启动整理超时，请稍后重试。')
    await fetchOrganizeProgress()
    ElMessage.success('整理任务已启动')
  } catch (error) {
    await fetchOrganizeProgress()
    throw error
  } finally {
    state.organizeLoading = false
  }
}

const pauseOrganize = async () => {
  await withActionTimeout(contentApi.pauseOrganize(route.params.id), 8000, '暂停整理超时，请稍后重试。')
  await fetchOrganizeProgress()
  ElMessage.success('已请求暂停整理')
}

const resumeOrganize = async () => {
  await withActionTimeout(contentApi.resumeOrganize(route.params.id), 8000, '继续整理超时，请稍后重试。')
  await fetchOrganizeProgress()
  ElMessage.success('已请求继续整理')
}

const cancelOrganize = async () => {
  await withActionTimeout(contentApi.cancelOrganize(route.params.id), 8000, '取消整理超时，请稍后重试。')
  await fetchOrganizeProgress()
  ElMessage.success('已请求取消整理')
}

const retryOrganize = async () => {
  state.organizeLoading = true
  try {
    await withActionTimeout(contentApi.retryOrganize(route.params.id, 'rebuild_global'), 8000, '重新整理超时，请稍后重试。')
    await fetchOrganizeProgress()
    ElMessage.success('已重新开始整理')
  } catch (error) {
    await fetchOrganizeProgress()
    throw error
  } finally {
    state.organizeLoading = false
  }
}

const generateBranches = async () => {
  if (!projectId.value) return
  state.branchLoading = true
  try {
    const result = await withActionTimeout(projectApi.branchesV2(projectId.value, { branch_count: 4 }), 12000, '生成分支超时，请稍后重试。')
    state.branches = result?.branches || []
    selectedBranchId.value = state.branches[0]?.id || ''
    if (selectedBranchId.value) window.localStorage.setItem(branchStorageKey.value, selectedBranchId.value)
    ElMessage.success('分支生成完成')
  } finally {
    state.branchLoading = false
  }
}

const createChapter = () => {
  cancelPendingWork()
  router.push(`/novel/${route.params.id}/chapters/new`)
}

const editChapter = (chapter) => {
  cancelPendingWork()
  router.push(`/novel/${route.params.id}/chapters/${chapter.id}/edit`)
}

const importChapter = (chapter) => {
  cancelPendingWork()
  router.push(`/novel/${route.params.id}/chapters/${chapter.id}/edit`)
}

const importChapterEntry = () => {
  ElMessage.info('请进入章节编辑页后执行具体单章导入')
}

const deleteChapter = async (chapter) => {
  await ElMessageBox.confirm(`确认删除《${chapter.title || `第${chapter.number}章`}》吗？`, '删除章节', { type: 'warning' })
  await withActionTimeout(novelApi.deleteChapter(route.params.id, chapter.id), 8000, '删除章节超时，请稍后重试。')
  ElMessage.success('章节已删除')
  await loadPage()
}

const goToWrite = () => {
  cancelPendingWork()
  if (selectedBranchId.value) {
    window.localStorage.setItem(branchStorageKey.value, selectedBranchId.value)
  }
  router.push({ path: `/novel/${route.params.id}/write`, query: selectedBranchId.value ? { branchId: selectedBranchId.value } : {} })
}

const goToWriteWithAssistant = () => {
  cancelPendingWork()
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
  cancelPendingWork()
  router.push('/import')
}

const goToOutlineImport = () => {
  cancelPendingWork()
  router.push('/import')
  ElMessage.info('请在导入页填写大纲文件路径后继续导入')
}

const exportNovel = async () => {
  exporting.value = true
  try {
    const result = await withActionTimeout(exportApi.export({
      novel_id: route.params.id,
      output_path: exportForm.value.outputPath,
      format: exportForm.value.format,
      scope: exportForm.value.scope,
      options: {
        chapter_export_mode: exportForm.value.chapterMode
      }
    }), 12000, '导出超时，请稍后重试。')
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
  cancelPendingWork()
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
onBeforeRouteLeave(() => {
  cancelPendingWork()
})
onBeforeUnmount(() => {
  cancelPendingWork()
})

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
