<template>
  <section class="ai-panel" data-test="ai-panel">
    <header class="ai-panel-header">
      <div>
        <h3>AI 助手</h3>
        <p>最小集成入口：设置、初始化、ContextPack、续写、Quick Trial、AIReview。</p>
      </div>
    </header>

    <div class="ai-section">
      <h4>AI 设置</h4>
      <div class="ai-meta">
        <span v-for="provider in providerConfigs" :key="provider.provider_name" class="tag">
          {{ provider.provider_name }} / {{ provider.default_model || '未设置模型' }}
        </span>
      </div>
      <div class="ai-actions">
        <button data-test="ai-test-provider" type="button" @click="handleTestProvider">测试 Provider</button>
      </div>
      <p v-if="providerTestMessage" class="ai-note">{{ providerTestMessage }}</p>
    </div>

    <div class="ai-section">
      <h4>初始化分析</h4>
      <div class="ai-actions">
        <button data-test="ai-start-initialization" type="button" @click="handleStartInitialization">启动初始化</button>
        <button
          v-if="polling.jobId"
          data-test="ai-cancel-job"
          type="button"
          @click="handleCancelJob"
        >
          取消任务
        </button>
      </div>
      <div class="ai-meta">
        <span v-if="initializationInfo.initialization_id">init {{ initializationInfo.initialization_id }}</span>
        <span v-if="polling.jobId">job {{ polling.jobId }}</span>
        <span v-if="jobStatusText">{{ jobStatusText }}</span>
        <span>分析成功 {{ initializationSummary.analyzed }}</span>
        <span>空章节 {{ initializationSummary.empty }}</span>
        <span>失败章节 {{ initializationSummary.failed }}</span>
      </div>
      <ul v-if="jobSteps.length" class="ai-list">
        <li v-for="step in jobSteps" :key="step.step_id">{{ step.step_name }} / {{ step.status }}</li>
      </ul>
      <p v-if="polling.error" class="ai-error">{{ polling.error }}</p>
    </div>

    <div class="ai-section">
      <h4>ContextPack</h4>
      <div class="ai-actions">
        <button data-test="ai-build-context-pack" type="button" @click="handleBuildContextPack">构建 ContextPack</button>
      </div>
      <div class="ai-meta">
        <span>readiness {{ contextPackReadiness.status || 'unknown' }}</span>
        <span v-if="contextPackReadiness.blocked_reason">blocked: {{ contextPackReadiness.blocked_reason }}</span>
        <span v-if="contextPackReadiness.degraded_reason">degraded: {{ contextPackReadiness.degraded_reason }}</span>
      </div>
      <ul v-if="contextPackItems.length" class="ai-list">
        <li v-for="item in contextPackItems" :key="item.item_id || item.source_type">
          {{ item.source_type || item.item_type }} / {{ item.content_text || item.summary || 'summary' }}
        </li>
      </ul>
    </div>

    <div v-if="plotArcVisible" class="ai-section">
      <h4>剧情轨道</h4>
      <div class="ai-meta">
        <span>{{ contextPackReadiness.status || 'unknown' }}</span>
        <span v-if="masterArcSummary.arc_title">{{ masterArcSummary.arc_title }}</span>
        <span v-if="volumeArcSummary.stage_goal">{{ volumeArcSummary.stage_goal }}</span>
      </div>
      <ul class="ai-list">
        <li v-if="sequenceArcSummary.sequence_goal">
          {{ sequenceArcSummary.sequence_goal }}
        </li>
        <li v-for="event in sequenceKeyEvents" :key="event">{{ event }}</li>
        <li v-for="summary in immediateRecentSummary" :key="summary">{{ summary }}</li>
        <li v-for="thread in immediateThreads" :key="thread">{{ thread }}</li>
      </ul>
      <div class="ai-meta">
        <span v-for="(value, key) in plotArcStatuses" :key="key">
          {{ key }}: {{ value.status || 'unknown' }}
        </span>
      </div>
    </div>

    <div class="ai-section">
      <h4>方向推演</h4>
      <div class="ai-actions">
        <button data-test="ai-generate-directions" type="button" @click="handleGenerateDirections">生成方向</button>
      </div>
      <ul v-if="directionProposals.length" class="ai-list">
        <li v-for="proposal in directionProposals" :key="proposal.direction_proposal_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ proposal.direction_proposal_id }}</strong>
            <span>{{ proposal.status }}</span>
          </div>
          <ul class="ai-list">
            <li v-for="option in proposal.options || []" :key="option.option_id" class="planning-option">
              <div class="candidate-summary">
                <strong>{{ option.label }}</strong>
                <span>{{ option.plot_summary }}</span>
              </div>
              <div class="ai-actions">
                <button
                  :data-test="`select-direction-${proposal.direction_proposal_id}-${option.option_id}`"
                  type="button"
                  @click="handleSelectDirection(proposal.direction_proposal_id, option.option_id)"
                >
                  选择方向
                </button>
              </div>
            </li>
          </ul>
          <div class="ai-actions">
            <button
              :data-test="`generate-plan-${proposal.direction_proposal_id}`"
              type="button"
              @click="handleGeneratePlan(proposal.direction_proposal_id)"
            >
              生成计划
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div class="ai-section">
      <h4>章节计划</h4>
      <ul v-if="chapterPlans.length" class="ai-list">
        <li v-for="plan in chapterPlans" :key="plan.chapter_plan_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ plan.chapter_plan_id }}</strong>
            <span>{{ plan.status }}</span>
            <span>{{ plan.plan_summary }}</span>
          </div>
          <ul class="ai-list">
            <li v-for="item in plan.plan_items || []" :key="item.item_id">
              {{ item.chapter_goal }}
            </li>
          </ul>
          <div class="ai-actions">
            <button
              :data-test="`confirm-plan-${plan.chapter_plan_id}`"
              type="button"
              @click="handleConfirmPlan(plan.chapter_plan_id)"
            >
              确认计划
            </button>
            <button
              :data-test="`reject-plan-${plan.chapter_plan_id}`"
              type="button"
              @click="handleRejectPlan(plan.chapter_plan_id)"
            >
              拒绝计划
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div class="ai-section">
      <h4>写作任务</h4>
      <ul v-if="writingTasks.length" class="ai-list">
        <li v-for="task in writingTasks" :key="task.writing_task_id">
          <div class="candidate-summary">
            <strong>{{ task.writing_task_id }}</strong>
            <span>{{ task.status }}</span>
            <span>{{ task.writing_goal }}</span>
            <span>{{ task.plan_summary }}</span>
          </div>
        </li>
      </ul>
      <p v-if="planningActionError" class="ai-error">{{ planningActionError }}</p>
    </div>

    <div class="ai-section">
      <h4>续写与候选稿</h4>
      <div
        v-if="conflictSummary.blockingCount || conflictSummary.warningCount"
        class="conflict-banner"
        data-test="conflict-banner"
        :class="{
          'conflict-banner-warning': !conflictSummary.blockingCount && conflictSummary.warningCount,
          'conflict-banner-blocking': conflictSummary.blockingCount > 0
        }"
      >
        <strong>{{ conflictSummary.blockingCount ? '资产冲突需处理' : '资产风险需确认' }}</strong>
        <span v-if="conflictSummary.blockingCount">存在 blocking {{ conflictSummary.blockingCount }}，apply 前必须处理。</span>
        <span v-else>存在 warning {{ conflictSummary.warningCount }}，继续 apply 代表已知风险。</span>
      </div>
      <div class="ai-actions">
        <button data-test="ai-start-continuation" type="button" @click="handleStartContinuation">生成候选稿</button>
      </div>
      <div class="ai-meta">
        <span v-if="continuationResult.job_id">续写 job {{ continuationResult.job_id }}</span>
        <span v-if="continuationResult.candidate_draft_id">candidate {{ continuationResult.candidate_draft_id }}</span>
      </div>
      <ul class="ai-list">
        <li v-for="item in candidateDrafts" :key="item.candidate_draft_id" class="candidate-item">
          <div class="candidate-summary">
            <strong>{{ item.candidate_draft_id }}</strong>
            <span>{{ item.content_preview }}</span>
            <span>{{ item.validation_status }}</span>
            <span>{{ item.source_context_pack_id }}</span>
            <span v-if="conflictCountsByDraft[item.candidate_draft_id]?.warning">warning {{ conflictCountsByDraft[item.candidate_draft_id].warning }}</span>
            <span v-if="conflictCountsByDraft[item.candidate_draft_id]?.blocking">blocking {{ conflictCountsByDraft[item.candidate_draft_id].blocking }}</span>
            <span v-if="conflictCountsByDraft[item.candidate_draft_id]?.info">info {{ conflictCountsByDraft[item.candidate_draft_id].info }}</span>
            <span v-if="item.selected_version_id">已选择版本 {{ item.selected_version_id }}</span>
            <span v-if="item.accepted_version_id">已接受版本 {{ item.accepted_version_id }}</span>
            <span v-if="item.applied_version_id">已应用版本 {{ item.applied_version_id }}</span>
          </div>
          <div class="ai-actions">
            <button :data-test="`candidate-detail-${item.candidate_draft_id}`" type="button" @click="loadCandidateDetail(item.candidate_draft_id)">
              查看详情
            </button>
            <button :data-test="`candidate-accept-${item.candidate_draft_id}`" type="button" @click="handleAcceptCandidate(item.candidate_draft_id)">
              accept
            </button>
            <button :data-test="`candidate-reject-${item.candidate_draft_id}`" type="button" @click="handleRejectCandidate(item.candidate_draft_id)">
              reject
            </button>
            <button :data-test="`candidate-apply-${item.candidate_draft_id}`" type="button" @click="handleApplyCandidate(item.candidate_draft_id)">
              apply
            </button>
            <button :data-test="`candidate-review-${item.candidate_draft_id}`" type="button" @click="handleReviewCandidate(item.candidate_draft_id)">
              AIReview
            </button>
          </div>
          <pre v-if="candidateDetails[item.candidate_draft_id]" class="candidate-detail">{{ candidateDetails[item.candidate_draft_id].content }}</pre>
          <div v-if="candidateDetails[item.candidate_draft_id]" class="ai-meta">
            <span>已选择版本 {{ selectedVersionByDraft[item.candidate_draft_id] || candidateDetails[item.candidate_draft_id].selected_version_id || '-' }}</span>
            <span>已接受版本 {{ candidateDetails[item.candidate_draft_id].accepted_version_id || '-' }}</span>
            <span>已应用版本 {{ candidateDetails[item.candidate_draft_id].applied_version_id || '-' }}</span>
          </div>
          <ul v-if="candidateVersions[item.candidate_draft_id]?.length" class="ai-list">
            <li
              v-for="(version, index) in candidateVersions[item.candidate_draft_id]"
              :key="version.candidate_version_id"
              class="planning-item"
            >
              <div class="candidate-summary">
                <strong>{{ version.candidate_version_id }}</strong>
                <span>v{{ version.version_no }}</span>
                <span>{{ version.status }}</span>
                <span>{{ version.content_summary }}</span>
              </div>
              <div class="ai-actions">
                <button
                  :data-test="`candidate-version-detail-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleCandidateVersionDetail(item.candidate_draft_id, version.candidate_version_id)"
                >
                  查看版本
                </button>
                <button
                  :data-test="`candidate-version-select-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleSelectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                >
                  选择版本
                </button>
                <button
                  v-if="index > 0"
                  :data-test="`candidate-version-diff-${item.candidate_draft_id}-${candidateVersions[item.candidate_draft_id][index - 1].candidate_version_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleCandidateVersionDiff(item.candidate_draft_id, candidateVersions[item.candidate_draft_id][index - 1].candidate_version_id, version.candidate_version_id)"
                >
                  查看 diff
                </button>
                <button
                  :data-test="`candidate-version-rewrite-review-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'review_based')"
                >
                  按审阅意见修订
                </button>
                <button
                  :data-test="`candidate-version-rewrite-user-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'user_instruction')"
                >
                  输入要求后重写
                </button>
                <button
                  :data-test="`candidate-version-reject-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleRejectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                >
                  拒绝此版本
                </button>
              </div>
              <pre v-if="candidateVersionDetails[version.candidate_version_id]" class="candidate-detail">{{ candidateVersionDetails[version.candidate_version_id].content }}</pre>
            </li>
          </ul>
          <div v-if="candidateReviewByDraft[item.candidate_draft_id]" class="ai-note">
            {{ candidateReviewByDraft[item.candidate_draft_id].summary }}
          </div>
          <div v-if="candidateVersionDiffs[item.candidate_draft_id]" class="ai-note">
            {{ candidateVersionDiffs[item.candidate_draft_id].summary }}
          </div>
          <ul v-if="conflictsByDraft[item.candidate_draft_id]?.length" class="ai-list">
            <li v-for="conflict in conflictsByDraft[item.candidate_draft_id]" :key="conflict.record_id" class="planning-item">
              <div class="candidate-summary">
                <strong>{{ conflict.title }}</strong>
                <span>{{ conflict.conflict_type }}</span>
                <span>{{ conflict.severity }}</span>
                <span>{{ conflict.summary }}</span>
              </div>
              <div class="ai-actions">
                <button :data-test="`conflict-detail-${conflict.record_id}`" type="button" @click="handleConflictDetail(conflict.record_id)">
                  查看冲突
                </button>
                <button
                  v-if="conflict.candidate_version_id"
                  :data-test="`conflict-rewrite-${conflict.record_id}`"
                  type="button"
                  @click="handleConflictRewrite(conflict)"
                >
                  启动修订
                </button>
                <button
                  v-if="conflict.candidate_version_id"
                  :data-test="`conflict-reject-${conflict.record_id}`"
                  type="button"
                  @click="handleConflictReject(conflict)"
                >
                  拒绝版本
                </button>
                <button
                  :data-test="`conflict-ack-${conflict.record_id}`"
                  type="button"
                  @click="handleConflictDecision(conflict.record_id, 'acknowledged', 'keep_as_is')"
                >
                  已知风险
                </button>
                <button
                  v-if="conflict.severity !== 'blocking'"
                  :data-test="`conflict-dismiss-${conflict.record_id}`"
                  type="button"
                  @click="handleConflictDecision(conflict.record_id, 'dismissed', 'defer')"
                >
                  defer
                </button>
              </div>
              <div v-if="conflictDetails[conflict.record_id]" class="ai-note">
                {{ conflictDetails[conflict.record_id].summary }}
              </div>
            </li>
          </ul>
        </li>
      </ul>
      <p v-if="candidateActionError" class="ai-error">{{ candidateActionError }}</p>
    </div>

    <div class="ai-section">
      <h4>AI 建议</h4>
      <ul v-if="aiSuggestions.length" class="ai-list">
        <li v-for="item in aiSuggestions" :key="item.suggestion_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ item.title }}</strong>
            <span>{{ item.suggestion_type }}</span>
            <span>{{ item.severity }}</span>
            <span>{{ item.summary }}</span>
          </div>
          <div class="ai-actions">
            <button :data-test="`suggestion-detail-${item.suggestion_id}`" type="button" @click="handleSuggestionDetail(item.suggestion_id)">
              查看建议
            </button>
            <button :data-test="`suggestion-accept-${item.suggestion_id}`" type="button" @click="handleAcceptSuggestion(item.suggestion_id)">
              accept
            </button>
            <button :data-test="`suggestion-dismiss-${item.suggestion_id}`" type="button" @click="handleDismissSuggestion(item.suggestion_id)">
              dismiss
            </button>
            <button
              v-if="item.suggestion_type !== 'risk_warning'"
              :data-test="`suggestion-convert-${item.suggestion_id}`"
              type="button"
              @click="handleConvertSuggestion(item.suggestion_id)"
            >
              convert
            </button>
          </div>
          <div v-if="aiSuggestionDetails[item.suggestion_id]" class="ai-note">
            {{ aiSuggestionDetails[item.suggestion_id].summary }}
          </div>
        </li>
      </ul>
    </div>

    <div class="ai-section">
      <h4>Quick Trial</h4>
      <div class="field-grid">
        <input v-model="quickTrialForm.input_text" type="text" placeholder="临时 prompt" />
        <input v-model="quickTrialForm.model_role" type="text" placeholder="model_role" />
      </div>
      <div class="ai-actions">
        <button data-test="quick-trial-run" type="button" @click="handleRunQuickTrial">运行试跑</button>
      </div>
      <div class="ai-meta">
        <span v-if="quickTrialResult.status">{{ quickTrialResult.status }}</span>
        <span v-if="quickTrialResult.validation_status">{{ quickTrialResult.validation_status }}</span>
      </div>
      <pre v-if="quickTrialResult.output_text" class="quick-trial-output">{{ quickTrialResult.output_text }}</pre>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api'
import { useAIJobPolling } from '@/composables/useAIJobPolling'

const props = defineProps({
  workId: {
    type: String,
    default: ''
  },
  chapterId: {
    type: String,
    default: ''
  },
  chapterVersion: {
    type: Number,
    default: 0
  }
})

const settings = ref({ provider_configs: [], model_role_mappings: {} })
const providerTestMessage = ref('')
const initializationInfo = ref({})
const contextPackReadiness = ref({})
const contextPackItems = ref([])
const continuationResult = ref({})
const candidateDrafts = ref([])
const candidateDetails = ref({})
const candidateVersions = ref({})
const candidateVersionDetails = ref({})
const candidateVersionDiffs = ref({})
const selectedVersionByDraft = ref({})
const candidateReviewByDraft = ref({})
const aiSuggestions = ref([])
const aiSuggestionDetails = ref({})
const conflicts = ref([])
const conflictDetails = ref({})
const candidateActionError = ref('')
const directionProposals = ref([])
const chapterPlans = ref([])
const writingTasks = ref([])
const planningActionError = ref('')
const quickTrialResult = ref({})
const polling = useAIJobPolling({ intervalMs: 1000 })

const quickTrialForm = reactive({
  input_text: '请试写一小段灯塔夜景。',
  model_role: 'quick_trial_writer'
})

const providerConfigs = computed(() => settings.value?.provider_configs || [])
const jobSteps = computed(() => polling.job.value?.steps || [])
const jobStatusText = computed(() => String(polling.job.value?.status || ''))
const plotArcStatuses = computed(() => contextPackReadiness.value?.plot_arc_statuses || {})
const plotArcSummary = computed(() => contextPackReadiness.value?.plot_arc_summary || {})
const masterArcSummary = computed(() => plotArcSummary.value?.master_arc || {})
const volumeArcSummary = computed(() => plotArcSummary.value?.volume_arc || {})
const sequenceArcSummary = computed(() => plotArcSummary.value?.sequence_arc || {})
const immediateSummary = computed(() => plotArcSummary.value?.immediate_window || {})
const sequenceKeyEvents = computed(() => {
  const items = sequenceArcSummary.value?.key_events
  return Array.isArray(items) ? items.filter(Boolean) : []
})
const immediateRecentSummary = computed(() => {
  const items = immediateSummary.value?.recent_chapters_summary
  return Array.isArray(items) ? items.filter(Boolean) : []
})
const immediateThreads = computed(() => {
  const items = immediateSummary.value?.active_plot_threads
  return Array.isArray(items) ? items.filter(Boolean) : []
})
const plotArcVisible = computed(() => Boolean(
  masterArcSummary.value.arc_title ||
  volumeArcSummary.value.stage_goal ||
  sequenceArcSummary.value.sequence_goal ||
  sequenceKeyEvents.value.length ||
  immediateRecentSummary.value.length ||
  immediateThreads.value.length ||
  Object.keys(plotArcStatuses.value).length
))
const initializationSummary = computed(() => ({
  analyzed: Number(initializationInfo.value?.analyzed_chapter_count || initializationInfo.value?.data?.analyzed_chapter_count || 0),
  empty: Number(initializationInfo.value?.empty_chapter_count || initializationInfo.value?.data?.empty_chapter_count || 0),
  failed: Number(initializationInfo.value?.failed_chapter_count || initializationInfo.value?.data?.failed_chapter_count || 0)
}))
const conflictCountsByDraft = computed(() => {
  const grouped = {}
  for (const item of conflicts.value) {
    const draftId = item.candidate_draft_id || ''
    if (!draftId) continue
    if (!grouped[draftId]) grouped[draftId] = { blocking: 0, warning: 0, info: 0 }
    if (item.severity === 'blocking') grouped[draftId].blocking += 1
    else if (item.severity === 'warning') grouped[draftId].warning += 1
    else grouped[draftId].info += 1
  }
  return grouped
})
const conflictsByDraft = computed(() => {
  const grouped = {}
  for (const item of conflicts.value) {
    const draftId = item.candidate_draft_id || ''
    if (!draftId) continue
    if (!grouped[draftId]) grouped[draftId] = []
    grouped[draftId].push(item)
  }
  return grouped
})
const conflictSummary = computed(() => conflicts.value.reduce((acc, item) => {
  if (item.severity === 'blocking') acc.blockingCount += 1
  else if (item.severity === 'warning') acc.warningCount += 1
  else acc.infoCount += 1
  return acc
}, { blockingCount: 0, warningCount: 0, infoCount: 0 }))

const unwrapData = (payload) => payload?.data ?? payload ?? {}

const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

const loadSettings = async () => {
  settings.value = unwrapData(await aiApi.getAISettings())
}

const loadInitialization = async () => {
  if (!props.workId) return
  try {
    initializationInfo.value = unwrapData(await aiApi.getLatestInitialization(props.workId))
  } catch (error) {
    initializationInfo.value = {}
  }
}

const loadContextReadiness = async () => {
  if (!props.workId) return
  try {
    contextPackReadiness.value = unwrapData(await aiApi.getContextPackReadiness(props.workId, props.chapterId))
  } catch (error) {
    contextPackReadiness.value = {}
  }
}

const loadCandidateDrafts = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listCandidateDrafts({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  candidateDrafts.value = payload.items || []
}

const loadPlanningData = async () => {
  if (!props.workId) return
  const [proposalsPayload, plansPayload, tasksPayload] = await Promise.all([
    aiApi.listDirectionProposals({
      work_id: props.workId,
      chapter_id: props.chapterId
    }),
    aiApi.listChapterPlans({
      work_id: props.workId,
      chapter_id: props.chapterId
    }),
    aiApi.listWritingTasks({
      work_id: props.workId,
      chapter_id: props.chapterId
    })
  ])
  directionProposals.value = unwrapData(proposalsPayload).items || []
  chapterPlans.value = unwrapData(plansPayload).items || []
  writingTasks.value = unwrapData(tasksPayload).items || []
}

const loadAISuggestions = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listAISuggestions({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  aiSuggestions.value = payload.items || []
}

const loadConflicts = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listConflicts({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  conflicts.value = payload.items || []
}

const refreshPanel = async () => {
  await Promise.all([
    loadSettings(),
    loadInitialization(),
    loadContextReadiness(),
    loadCandidateDrafts(),
    loadPlanningData(),
    loadAISuggestions(),
    loadConflicts()
  ])
}

const handleTestProvider = async () => {
  const providerName = providerConfigs.value[0]?.provider_name || 'fake'
  const modelName = providerConfigs.value[0]?.default_model || 'fake-chat'
  const payload = unwrapData(await aiApi.testProvider(providerName, { model_name: modelName }))
  providerTestMessage.value = payload.message || payload.test_status || 'ok'
}

const handleStartInitialization = async () => {
  const payload = unwrapData(await aiApi.startInitialization({ work_id: props.workId }))
  initializationInfo.value = payload
  if (payload.job_id) {
    await polling.start(payload.job_id)
  }
}

const handleCancelJob = async () => {
  if (!polling.jobId.value) return
  await aiApi.cancelAIJob(polling.jobId.value, { reason: 'user_cancelled' })
  await polling.fetchOnce()
}

const handleBuildContextPack = async () => {
  const buildPayload = unwrapData(await aiApi.buildContextPack({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  contextPackReadiness.value = {
    ...contextPackReadiness.value,
    ...buildPayload
  }
  try {
    const latestPayload = unwrapData(await aiApi.getLatestContextPack(props.workId, props.chapterId))
    contextPackItems.value = latestPayload.context_items || []
  } catch (error) {
    contextPackItems.value = []
  }
}

const handleStartContinuation = async () => {
  continuationResult.value = unwrapData(await aiApi.startContinuation({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  await loadCandidateDrafts()
}

const handleGenerateDirections = async () => {
  planningActionError.value = ''
  try {
    await aiApi.generateDirectionProposal({
      work_id: props.workId,
      chapter_id: props.chapterId,
      user_instruction: '继续推进当前章节主线',
      caller_type: 'user_action',
      idempotency_key: buildIdempotencyKey('direction_generate')
    })
    await loadPlanningData()
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || 'direction generate failed')
  }
}

const handleSelectDirection = async (proposalId, optionId) => {
  planningActionError.value = ''
  try {
    await aiApi.selectDirection(proposalId, {
      selected_option_id: optionId,
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      idempotency_key: buildIdempotencyKey('direction_select')
    })
    await loadPlanningData()
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || 'direction select failed')
  }
}

const handleGeneratePlan = async (proposalId) => {
  planningActionError.value = ''
  try {
    await aiApi.generateChapterPlan({
      work_id: props.workId,
      chapter_id: props.chapterId,
      direction_proposal_id: proposalId,
      caller_type: 'user_action',
      idempotency_key: buildIdempotencyKey('chapter_plan_generate')
    })
    await loadPlanningData()
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || 'chapter plan generate failed')
  }
}

const handleConfirmPlan = async (planId) => {
  planningActionError.value = ''
  try {
    await aiApi.confirmChapterPlan(planId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      idempotency_key: buildIdempotencyKey('chapter_plan_confirm')
    })
    await loadPlanningData()
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || 'chapter plan confirm failed')
  }
}

const handleRejectPlan = async (planId) => {
  planningActionError.value = ''
  try {
    await aiApi.rejectChapterPlan(planId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      user_edit_notes: '当前计划推进过快',
      idempotency_key: buildIdempotencyKey('chapter_plan_reject')
    })
    await loadPlanningData()
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || 'chapter plan reject failed')
  }
}

const loadCandidateDetail = async (candidateDraftId) => {
  const [payload, versionsPayload] = await Promise.all([
    aiApi.getCandidateDraft(candidateDraftId),
    aiApi.listCandidateDraftVersions(candidateDraftId)
  ])
  const detail = unwrapData(payload)
  candidateDetails.value = {
    ...candidateDetails.value,
    [candidateDraftId]: detail
  }
  candidateVersions.value = {
    ...candidateVersions.value,
    [candidateDraftId]: unwrapData(versionsPayload).items || []
  }
  selectedVersionByDraft.value = {
    ...selectedVersionByDraft.value,
    [candidateDraftId]: detail.selected_version_id || (unwrapData(versionsPayload).items?.[0]?.candidate_version_id || '')
  }
}

const handleAcceptCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.acceptCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      candidate_version_id: selectedVersionByDraft.value[candidateDraftId] || candidateDetails.value[candidateDraftId]?.selected_version_id || '',
      idempotency_key: buildIdempotencyKey('candidate_accept')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'accept failed')
  }
}

const handleRejectCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      candidate_version_id: selectedVersionByDraft.value[candidateDraftId] || candidateDetails.value[candidateDraftId]?.selected_version_id || '',
      reason: 'manual reject',
      idempotency_key: buildIdempotencyKey('candidate_reject')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'reject failed')
  }
}

const handleApplyCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    const draftConflicts = conflictsByDraft.value[candidateDraftId] || []
    const hasBlocking = draftConflicts.some((item) => item.severity === 'blocking')
    const warningItems = draftConflicts.filter((item) => item.severity === 'warning')
    if (hasBlocking) {
      candidateActionError.value = 'blocking_conflict_unresolved'
      return
    }
    if (warningItems.length) {
      const confirmed = window.confirm(
        `存在 ${warningItems.length} 条 warning。继续 apply 代表已知风险，是否继续？`
      )
      if (!confirmed) return
    }
    await aiApi.applyCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      candidate_version_id: selectedVersionByDraft.value[candidateDraftId] || candidateDetails.value[candidateDraftId]?.selected_version_id || '',
      expected_chapter_version: props.chapterVersion,
      idempotency_key: buildIdempotencyKey('candidate_apply')
    })
    ElMessage.success('apply 成功')
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'apply failed')
  }
}

const handleRunQuickTrial = async () => {
  quickTrialResult.value = unwrapData(await aiApi.runQuickTrial({
    model_role: quickTrialForm.model_role,
    input_text: quickTrialForm.input_text
  }))
}

const handleReviewCandidate = async (candidateDraftId) => {
  const payload = unwrapData(await aiApi.reviewCandidateDraft(candidateDraftId, { user_instruction: '' }))
  let reviewDetail = payload
  if (payload.review_id) {
    try {
      reviewDetail = unwrapData(await aiApi.getAIReview(payload.review_id))
    } catch (error) {
      reviewDetail = payload
    }
  }
  candidateReviewByDraft.value = {
    ...candidateReviewByDraft.value,
    [candidateDraftId]: reviewDetail
  }
  await loadAISuggestions()
}

const handleCandidateVersionDetail = async (candidateDraftId, candidateVersionId) => {
  const payload = unwrapData(await aiApi.getCandidateDraftVersion(candidateDraftId, candidateVersionId))
  candidateVersionDetails.value = {
    ...candidateVersionDetails.value,
    [candidateVersionId]: payload
  }
}

const handleSelectCandidateVersion = async (candidateDraftId, candidateVersionId) => {
  candidateActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.selectCandidateDraftVersion(candidateDraftId, candidateVersionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      idempotency_key: buildIdempotencyKey('candidate_select')
    }))
    selectedVersionByDraft.value = {
      ...selectedVersionByDraft.value,
      [candidateDraftId]: candidateVersionId
    }
    candidateDetails.value = {
      ...candidateDetails.value,
      [candidateDraftId]: payload
    }
    await loadCandidateDrafts()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'select version failed')
  }
}

const handleCandidateVersionDiff = async (candidateDraftId, fromVersionId, toVersionId) => {
  const payload = unwrapData(await aiApi.getCandidateDraftVersionDiff(candidateDraftId, {
    from_version_id: fromVersionId,
    to_version_id: toVersionId
  }))
  candidateVersionDiffs.value = {
    ...candidateVersionDiffs.value,
    [candidateDraftId]: payload
  }
}

const handleRewriteCandidate = async (candidateDraftId, candidateVersionId, triggerType) => {
  candidateActionError.value = ''
  try {
    await aiApi.rewriteCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      source_version_id: candidateVersionId,
      trigger_type: triggerType,
      review_report_id: candidateReviewByDraft.value[candidateDraftId]?.review_id || '',
      user_instruction: triggerType === 'user_instruction' ? '请强化父亲留下的地图线索。' : '',
      idempotency_key: buildIdempotencyKey('candidate_rewrite')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'rewrite failed')
  }
}

const handleRejectCandidateVersion = async (candidateDraftId, candidateVersionId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraftVersion(candidateDraftId, candidateVersionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      reason: 'manual reject current version',
      idempotency_key: buildIdempotencyKey('candidate_version_reject')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'reject version failed')
  }
}

const handleSuggestionDetail = async (suggestionId) => {
  const payload = unwrapData(await aiApi.getAISuggestion(suggestionId))
  aiSuggestionDetails.value = {
    ...aiSuggestionDetails.value,
    [suggestionId]: payload
  }
}

const handleConflictDetail = async (recordId) => {
  const payload = unwrapData(await aiApi.getConflict(recordId))
  conflictDetails.value = {
    ...conflictDetails.value,
    [recordId]: payload
  }
}

const handleConflictDecision = async (recordId, decision, decisionNote = '') => {
  await aiApi.decideConflict(recordId, {
    caller_type: 'user_action',
    user_action: true,
    user_id: 'ui-user',
    decision,
    decision_note: decisionNote || (decision === 'dismissed' ? 'manual defer' : 'manual acknowledge'),
    idempotency_key: buildIdempotencyKey('conflict_decide')
  })
  await loadConflicts()
}

const handleConflictRewrite = async (conflict) => {
  await handleRewriteCandidate(
    conflict.candidate_draft_id,
    conflict.candidate_version_id || selectedVersionByDraft.value[conflict.candidate_draft_id] || '',
    'review_based'
  )
  await handleConflictDecision(conflict.record_id, 'acknowledged', 'revise_candidate')
}

const handleConflictReject = async (conflict) => {
  const candidateVersionId = conflict.candidate_version_id || selectedVersionByDraft.value[conflict.candidate_draft_id] || ''
  if (candidateVersionId) {
    await aiApi.rejectCandidateDraftVersion(conflict.candidate_draft_id, candidateVersionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      reason: 'conflict reject current version',
      idempotency_key: buildIdempotencyKey('conflict_candidate_version_reject')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(conflict.candidate_draft_id)
    await loadAISuggestions()
    await loadConflicts()
  }
  await handleConflictDecision(conflict.record_id, 'resolved', 'reject_candidate')
}

const handleAcceptSuggestion = async (suggestionId) => {
  await aiApi.acceptAISuggestion(suggestionId, {
    caller_type: 'user_action',
    user_action: true,
    user_id: 'ui-user',
    idempotency_key: buildIdempotencyKey('suggestion_accept')
  })
  await loadAISuggestions()
}

const handleDismissSuggestion = async (suggestionId) => {
  await aiApi.dismissAISuggestion(suggestionId, {
    caller_type: 'user_action',
    user_action: true,
    user_id: 'ui-user',
    decision_note: 'manual dismiss',
    idempotency_key: buildIdempotencyKey('suggestion_dismiss')
  })
  await loadAISuggestions()
}

const handleConvertSuggestion = async (suggestionId) => {
  const payload = unwrapData(await aiApi.convertAISuggestion(suggestionId, {
    caller_type: 'user_action',
    user_action: true,
    user_id: 'ui-user',
    idempotency_key: buildIdempotencyKey('suggestion_convert')
  }))
  const actionRef = String(payload?.action?.action_payload_ref || '')
  if (actionRef.startsWith('conflict_guard:')) {
    const recordId = actionRef.split(':').slice(1).join(':')
    if (recordId) {
      await handleConflictDetail(recordId)
      await loadConflicts()
    }
  }
  await loadAISuggestions()
}

watch(() => props.workId, async () => {
  await refreshPanel()
}, { immediate: true })

watch(() => props.chapterId, async () => {
  await Promise.all([loadContextReadiness(), loadCandidateDrafts(), loadPlanningData(), loadAISuggestions(), loadConflicts()])
}, { immediate: true })

onMounted(async () => {
  await refreshPanel()
})
</script>

<style scoped>
.ai-panel {
  display: grid;
  gap: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  background: #ffffff;
  padding: 16px;
}

.ai-panel-header h3,
.ai-section h4 {
  margin: 0;
  color: #111827;
}

.ai-panel-header p,
.ai-note,
.ai-error {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.ai-error {
  color: #b91c1c;
}

.ai-section {
  display: grid;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.conflict-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
}

.conflict-banner-warning {
  border: 1px solid #f59e0b;
  background: #fff7ed;
  color: #9a3412;
}

.conflict-banner-blocking {
  border: 1px solid #ef4444;
  background: #fef2f2;
  color: #991b1b;
}

.ai-actions,
.ai-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-actions button,
.field-grid input {
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
}

.ai-actions button {
  background: #f8fafc;
  cursor: pointer;
}

.tag {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
}

.ai-list {
  display: grid;
  gap: 8px;
  padding-left: 18px;
  margin: 0;
}

.candidate-item {
  display: grid;
  gap: 8px;
}

.planning-item,
.planning-option {
  display: grid;
  gap: 8px;
}

.candidate-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
}

.candidate-detail,
.quick-trial-output {
  white-space: pre-wrap;
  border-radius: 12px;
  background: #f8fafc;
  padding: 10px;
  margin: 0;
  font-size: 12px;
}

.field-grid {
  display: grid;
  gap: 8px;
}
</style>
