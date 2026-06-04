<template>
  <section class="review-tab" data-panel="review">
    <header class="review-header">
      <div>
        <h3>审阅工作区</h3>
        <p>候选稿、AI 建议、冲突提示、记忆审批与任务追踪都在这里集中处理。</p>
      </div>
    </header>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>候选稿与人工确认门</h4>
          <p>所有 AI 生成内容都会先进入候选稿，只有明确的用户操作才能接受、拒绝或应用到正文。</p>
        </div>
        <button
          type="button"
          class="primary-button"
          data-test="candidate-start-continuation"
          :disabled="!canOperate"
          @click="handleStartContinuation"
        >
          生成候选稿
        </button>
      </div>

      <div
        v-if="conflictSummary.blockingCount || conflictSummary.warningCount"
        class="status-banner"
        :class="{
          'status-banner--blocking': conflictSummary.blockingCount,
          'status-banner--warning': !conflictSummary.blockingCount && conflictSummary.warningCount
        }"
      >
        <strong>{{ conflictSummary.blockingCount ? '存在阻断冲突' : '存在风险提示' }}</strong>
        <span v-if="conflictSummary.blockingCount">
          当前有 {{ conflictSummary.blockingCount }} 条阻断冲突，处理完成后才能应用到正文。
        </span>
        <span v-else>
          当前有 {{ conflictSummary.warningCount }} 条风险提示，继续应用代表你已知晓风险。
        </span>
      </div>

      <ul v-if="candidateDrafts.length" class="entity-list">
        <li v-for="item in candidateDrafts" :key="item.candidate_draft_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ item.candidate_draft_id }}</strong>
            <span>{{ item.content_preview || '暂无预览' }}</span>
            <span>{{ displayValidationStatus(item.validation_status) }}</span>
            <span v-if="item.selected_version_id">当前版本 {{ item.selected_version_id }}</span>
            <span v-if="item.accepted_version_id">已接受 {{ item.accepted_version_id }}</span>
            <span v-if="item.applied_version_id">已应用 {{ item.applied_version_id }}</span>
          </div>

          <div class="action-row">
            <button type="button" :data-test="`candidate-detail-${item.candidate_draft_id}`" @click="loadCandidateDetail(item.candidate_draft_id)">
              查看详情
            </button>
            <button type="button" :data-test="`candidate-accept-${item.candidate_draft_id}`" @click="handleAcceptCandidate(item.candidate_draft_id)">
              接受当前版本
            </button>
            <button type="button" :data-test="`candidate-reject-${item.candidate_draft_id}`" @click="handleRejectCandidate(item.candidate_draft_id)">
              拒绝当前版本
            </button>
            <button type="button" :data-test="`candidate-apply-${item.candidate_draft_id}`" @click="handleApplyCandidate(item.candidate_draft_id)">
              应用到正文
            </button>
            <button type="button" :data-test="`candidate-review-${item.candidate_draft_id}`" @click="handleReviewCandidate(item.candidate_draft_id)">
              AI 审阅
            </button>
          </div>

          <div v-if="candidateDetails[item.candidate_draft_id]" class="detail-block">
            <pre class="detail-pre">{{ candidateDetails[item.candidate_draft_id].content }}</pre>
            <div class="detail-meta">
              <span>已选择 {{ selectedVersionByDraft[item.candidate_draft_id] || '-' }}</span>
              <span>已接受 {{ candidateDetails[item.candidate_draft_id].accepted_version_id || '-' }}</span>
              <span>已应用 {{ candidateDetails[item.candidate_draft_id].applied_version_id || '-' }}</span>
            </div>

            <ul v-if="candidateVersions[item.candidate_draft_id]?.length" class="nested-list">
              <li
                v-for="(version, index) in candidateVersions[item.candidate_draft_id]"
                :key="version.candidate_version_id"
                class="nested-card"
              >
                <div class="entity-summary">
                  <strong>{{ version.candidate_version_id }}</strong>
                  <span>v{{ version.version_no }}</span>
                  <span>{{ displayStatus(version.status) }}</span>
                  <span>{{ version.content_summary }}</span>
                </div>
                <div class="action-row">
                  <button
                    type="button"
                    :data-test="`candidate-version-detail-${item.candidate_draft_id}-${version.candidate_version_id}`"
                    @click="handleCandidateVersionDetail(item.candidate_draft_id, version.candidate_version_id)"
                  >
                    查看版本
                  </button>
                  <button
                    type="button"
                    :data-test="`candidate-version-select-${item.candidate_draft_id}-${version.candidate_version_id}`"
                    @click="handleSelectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                  >
                    选择版本
                  </button>
                  <button
                    v-if="index > 0"
                    type="button"
                    :data-test="`candidate-version-diff-${item.candidate_draft_id}-${candidateVersions[item.candidate_draft_id][index - 1].candidate_version_id}-${version.candidate_version_id}`"
                    @click="handleCandidateVersionDiff(item.candidate_draft_id, candidateVersions[item.candidate_draft_id][index - 1].candidate_version_id, version.candidate_version_id)"
                  >
                    查看差异
                  </button>
                  <button
                    type="button"
                    :data-test="`candidate-version-rewrite-review-${item.candidate_draft_id}-${version.candidate_version_id}`"
                    @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'review_based')"
                  >
                    按审阅意见修订
                  </button>
                  <button
                    type="button"
                    :data-test="`candidate-version-rewrite-user-${item.candidate_draft_id}-${version.candidate_version_id}`"
                    @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'user_instruction')"
                  >
                    输入要求后重写
                  </button>
                  <button
                    type="button"
                    :data-test="`candidate-version-reject-${item.candidate_draft_id}-${version.candidate_version_id}`"
                    @click="handleRejectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                  >
                    拒绝此版本
                  </button>
                </div>
                <pre v-if="candidateVersionDetails[version.candidate_version_id]" class="detail-pre">{{ candidateVersionDetails[version.candidate_version_id].content }}</pre>
              </li>
            </ul>

            <div v-if="candidateReviewByDraft[item.candidate_draft_id]" class="note-box">
              {{ candidateReviewByDraft[item.candidate_draft_id].summary }}
            </div>
            <div v-if="candidateVersionDiffs[item.candidate_draft_id]" class="note-box">
              {{ candidateVersionDiffs[item.candidate_draft_id].summary }}
            </div>

            <ul v-if="conflictsByDraft[item.candidate_draft_id]?.length" class="nested-list">
              <li v-for="conflict in conflictsByDraft[item.candidate_draft_id]" :key="conflict.record_id" class="nested-card">
                <div class="entity-summary">
                  <strong>{{ conflict.title }}</strong>
                  <span>{{ displayConflictType(conflict.conflict_type) }}</span>
                  <span>{{ displaySeverity(conflict.severity) }}</span>
                  <span>{{ conflict.summary }}</span>
                </div>
                <div class="action-row">
                  <button type="button" :data-test="`conflict-detail-${conflict.record_id}`" @click="handleConflictDetail(conflict.record_id)">
                    查看冲突
                  </button>
                  <button type="button" :data-test="`conflict-ack-${conflict.record_id}`" @click="handleConflictDecision(conflict.record_id, 'acknowledged', 'manual acknowledge')">
                    我已知晓
                  </button>
                  <button
                    v-if="conflict.severity !== 'blocking'"
                    type="button"
                    :data-test="`conflict-dismiss-${conflict.record_id}`"
                    @click="handleConflictDecision(conflict.record_id, 'dismissed', 'manual defer')"
                  >
                    稍后处理
                  </button>
                </div>
                <div v-if="conflictDetails[conflict.record_id]" class="note-box">
                  {{ conflictDetails[conflict.record_id].summary }}
                </div>
              </li>
            </ul>
          </div>
        </li>
      </ul>
      <div v-else class="empty-state">当前章节还没有候选稿。</div>
      <p v-if="candidateActionError" class="error-text">{{ candidateActionError }}</p>
    </section>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>AI 建议</h4>
          <p>AI 只给出建议，不会自动执行。你确认之后，它才会转成后续动作。</p>
        </div>
      </div>
      <ul v-if="aiSuggestions.length" class="entity-list">
        <li v-for="item in aiSuggestions" :key="item.suggestion_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ item.title }}</strong>
            <span>{{ displaySuggestionType(item.suggestion_type) }}</span>
            <span>{{ displaySeverity(item.severity) }}</span>
            <span>{{ item.summary }}</span>
          </div>
          <div class="action-row">
            <button type="button" :data-test="`suggestion-detail-${item.suggestion_id}`" @click="handleSuggestionDetail(item.suggestion_id)">
              查看建议
            </button>
            <button type="button" :data-test="`suggestion-accept-${item.suggestion_id}`" @click="handleAcceptSuggestion(item.suggestion_id)">
              采纳建议
            </button>
            <button type="button" :data-test="`suggestion-dismiss-${item.suggestion_id}`" @click="handleDismissSuggestion(item.suggestion_id)">
              忽略建议
            </button>
            <button
              v-if="item.suggestion_type !== 'risk_warning'"
              type="button"
              :data-test="`suggestion-convert-${item.suggestion_id}`"
              @click="handleConvertSuggestion(item.suggestion_id)"
            >
              转为后续动作
            </button>
          </div>
          <div v-if="aiSuggestionDetails[item.suggestion_id]" class="note-box">
            {{ aiSuggestionDetails[item.suggestion_id].summary }}
          </div>
        </li>
      </ul>
      <div v-else class="empty-state">当前没有待处理的 AI 建议。</div>
    </section>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>记忆审批</h4>
          <p>记忆更新不会自动写入，必须经过独立审批后才能应用到正式记忆。</p>
        </div>
      </div>
      <ul v-if="memoryGates.length" class="entity-list">
        <li v-for="gate in memoryGates" :key="gate.gate_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ gate.gate_id }}</strong>
            <span>{{ displayStatus(gate.state) }}</span>
            <span>建议数 {{ (gate.suggestions || []).length }}</span>
          </div>

          <ul class="nested-list">
            <li v-for="suggestion in gate.suggestions || []" :key="suggestion.id" class="nested-card">
              <div class="entity-summary">
                <strong>{{ displayMemoryTargetType(suggestion.target_memory_type) }}</strong>
                <span>{{ displayRevisionType(suggestion.revision_type) }}</span>
                <span>{{ displayStatus(suggestion.status) }}</span>
                <span>{{ suggestion.current_value_summary }}</span>
                <span>{{ suggestion.proposed_value_summary }}</span>
              </div>
              <div class="action-row">
                <button type="button" :data-test="`memory-approve-${gate.gate_id}-${suggestion.id}`" @click="handleApproveMemorySuggestion(gate.gate_id, suggestion.id)">
                  审批通过
                </button>
                <button type="button" :data-test="`memory-edit-approve-${gate.gate_id}-${suggestion.id}`" @click="handleEditApproveMemorySuggestion(gate.gate_id, suggestion)">
                  修改后通过
                </button>
                <button type="button" :data-test="`memory-reject-${gate.gate_id}-${suggestion.id}`" @click="handleRejectMemorySuggestion(gate.gate_id, suggestion.id)">
                  拒绝建议
                </button>
                <button type="button" :data-test="`memory-defer-${gate.gate_id}-${suggestion.id}`" @click="handleDeferMemorySuggestion(gate.gate_id, suggestion.id)">
                  稍后处理
                </button>
              </div>
            </li>
          </ul>

          <div class="action-row gate-actions">
            <button type="button" :data-test="`memory-apply-${gate.gate_id}`" @click="handleApplyMemoryGate(gate.gate_id)">
              应用本组修订
            </button>
          </div>

          <ul v-if="gate.revision_ids?.length" class="nested-list">
            <li v-for="revisionId in gate.revision_ids" :key="revisionId" class="nested-card">
              <div class="entity-summary">
                <strong>{{ revisionId }}</strong>
                <span>{{ displayStatus(memoryRevisionDetails[revisionId]?.status || 'revision') }}</span>
              </div>
              <div class="action-row">
                <button type="button" :data-test="`memory-revision-detail-${revisionId}`" @click="handleMemoryRevisionDetail(revisionId)">
                  查看修订详情
                </button>
                <button
                  v-if="memoryRevisionDetails[revisionId]?.status === 'applied'"
                  type="button"
                  :data-test="`memory-revision-rollback-${revisionId}`"
                  @click="handleRollbackMemoryRevision(revisionId)"
                >
                  执行回滚
                </button>
              </div>
            </li>
          </ul>
        </li>
      </ul>
      <div v-else class="empty-state">当前没有待审批的记忆更新。</div>
      <p v-if="memoryActionError" class="error-text">{{ memoryActionError }}</p>
    </section>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>任务追踪</h4>
          <p>普通用户默认只看摘要，详细追踪只在开发者模式下展示。</p>
        </div>
      </div>
      <ul v-if="agentTraces.length" class="entity-list">
        <li v-for="trace in agentTraces" :key="trace.trace_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ trace.trace_id }}</strong>
            <span>{{ displayStatus(trace.status) }}</span>
            <span>{{ displayWorkflowType(trace.workflow_type) }}</span>
            <span>步骤数 {{ trace.total_steps || 0 }}</span>
            <span>Token {{ trace.total_tokens || 0 }}</span>
          </div>
          <div class="action-row">
            <button type="button" :data-test="`trace-steps-${trace.trace_id}`" @click="handleTraceSteps(trace.trace_id)">
              查看步骤
            </button>
            <button
              v-if="developerMode"
              type="button"
              :data-test="`trace-detail-${trace.trace_id}`"
              @click="handleTraceDetail(trace.trace_id)"
            >
              查看详细追踪
            </button>
          </div>
          <ul v-if="agentTraceSteps[trace.trace_id]?.length" class="nested-list">
            <li v-for="step in agentTraceSteps[trace.trace_id]" :key="step.step_id" class="nested-card">
              {{ displayAgentType(step.agent_type) }} / {{ displayStepAction(step.action) }} / {{ displayStatus(step.status) }}
            </li>
          </ul>
          <div v-if="agentTraceDetails[trace.trace_id]" class="note-box">
            {{ agentTraceDetails[trace.trace_id].summary || '详细追踪已加载。' }}
          </div>
        </li>
      </ul>
      <div v-else class="empty-state">当前没有任务追踪记录。</div>
      <p v-if="traceActionError" class="error-text">{{ traceActionError }}</p>
    </section>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api'

const props = defineProps({
  workId: { type: String, default: '' },
  chapterId: { type: String, default: '' },
  chapterVersion: { type: Number, default: 0 },
  developerMode: { type: Boolean, default: false }
})

const candidateDrafts = ref([])
const candidateDetails = ref({})
const candidateVersions = ref({})
const candidateVersionDetails = ref({})
const candidateVersionDiffs = ref({})
const selectedVersionByDraft = ref({})
const candidateReviewByDraft = ref({})
const continuationResult = ref({})
const aiSuggestions = ref([])
const aiSuggestionDetails = ref({})
const conflicts = ref([])
const conflictDetails = ref({})
const memoryGates = ref([])
const memoryRevisionDetails = ref({})
const agentTraces = ref([])
const agentTraceSteps = ref({})
const agentTraceDetails = ref({})

const candidateActionError = ref('')
const memoryActionError = ref('')
const traceActionError = ref('')

const canOperate = computed(() => Boolean(props.workId && props.chapterId))

const conflictsByDraft = computed(() => {
  return conflicts.value.reduce((accumulator, item) => {
    const draftId = String(item.candidate_draft_id || '')
    if (!draftId) return accumulator
    if (!accumulator[draftId]) accumulator[draftId] = []
    accumulator[draftId].push(item)
    return accumulator
  }, {})
})

const conflictSummary = computed(() => {
  return conflicts.value.reduce((summary, item) => {
    if (item.severity === 'blocking') summary.blockingCount += 1
    else if (item.severity === 'warning') summary.warningCount += 1
    return summary
  }, { blockingCount: 0, warningCount: 0 })
})

const statusLabels = {
  pending: '待开始',
  generated: '已生成',
  shown: '已展示',
  accepted: '已接受',
  rejected: '已拒绝',
  applied: '已应用',
  review_completed: '审阅完成',
  reviewing: '审阅中',
  waiting_for_user: '等待用户',
  completed: '已完成',
  completed_with_candidate: '已生成候选稿',
  running: '进行中',
  revision_requested: '已请求修订',
  superseded: '已有新版本',
  stale: '可能已过期',
  failed: '失败',
  acknowledged: '已知晓',
  dismissed: '已忽略',
  converted: '已转为后续动作',
  waiting_for_review: '等待审批',
  approved: '审批通过',
  detail: '已加载详情',
  revision: '修订记录'
}

const validationStatusLabels = {
  passed: '校验通过',
  failed: '校验失败',
  warning: '存在风险',
  skipped: '未校验'
}

const suggestionTypeLabels = {
  rewrite_suggestion: '改写建议',
  style_suggestion: '风格建议',
  plot_suggestion: '剧情建议',
  character_suggestion: '人物建议',
  foreshadow_suggestion: '伏笔建议',
  memory_update_suggestion_ref: '记忆更新建议',
  conflict_resolution_suggestion: '冲突处理建议',
  direction_plan_suggestion: '方向与计划建议',
  continuity_suggestion: '连续性建议',
  risk_warning: '风险提示'
}

const severityLabels = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '关键',
  info: '提示',
  warning: '警告',
  blocking: '阻断'
}

const conflictTypeLabels = {
  candidate_version_conflict: '候选版本冲突',
  character_conflict: '人物冲突',
  setting_conflict: '设定冲突',
  timeline_conflict: '时间线冲突',
  arc_conflict: '剧情轨道冲突',
  direction_plan_conflict: '方向计划冲突',
  memory_conflict: '记忆冲突',
  foreshadow_conflict: '伏笔冲突',
  user_draft_conflict: '正文草稿冲突',
  apply_version_conflict: '应用版本冲突',
  unknown_conflict: '未归类冲突'
}

const workflowTypeLabels = {
  continuation: '续写任务',
  revision: '修订任务',
  review: '审阅任务',
  planning: '规划任务'
}

const agentTypeLabels = {
  memory: '理解故事',
  planner: '规划方向',
  writer: '生成候选稿',
  reviewer: '审阅稿件',
  rewriter: '修订稿件'
}

const stepActionLabels = {
  review: '执行审阅',
  draft: '生成候选稿',
  revise: '执行修订',
  plan: '规划任务',
  analyze: '分析上下文'
}

const memoryTargetLabels = {
  character: '人物记忆',
  setting: '设定记忆',
  timeline: '时间线记忆',
  foreshadow: '伏笔记忆',
  plot_thread: '剧情线索',
  story_state: '章节状态',
  continuity_note: '连续性备注'
}

const revisionTypeLabels = {
  character_update: '人物更新',
  setting_update: '设定更新',
  timeline_event_add: '新增时间线事件',
  timeline_event_update: '更新时间线事件',
  foreshadow_add: '新增伏笔',
  foreshadow_update: '推进伏笔',
  foreshadow_resolve: '回收伏笔',
  plot_thread_update: '剧情线索更新',
  story_state_update: '章节状态更新',
  arc_note_update: '轨道备注更新',
  continuity_note_add: '连续性备注',
  unknown_memory_update: '未归类记忆更新'
}

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const displayStatus = (value) => statusLabels[String(value || '')] || String(value || '-')
const displayValidationStatus = (value) => validationStatusLabels[String(value || '')] || String(value || '-')
const displaySuggestionType = (value) => suggestionTypeLabels[String(value || '')] || String(value || '-')
const displaySeverity = (value) => severityLabels[String(value || '')] || String(value || '-')
const displayConflictType = (value) => conflictTypeLabels[String(value || '')] || String(value || '-')
const displayWorkflowType = (value) => workflowTypeLabels[String(value || '')] || String(value || '-')
const displayAgentType = (value) => agentTypeLabels[String(value || '')] || String(value || '-')
const displayStepAction = (value) => stepActionLabels[String(value || '')] || String(value || '-')
const displayMemoryTargetType = (value) => memoryTargetLabels[String(value || '')] || String(value || '-')
const displayRevisionType = (value) => revisionTypeLabels[String(value || '')] || String(value || '-')

const buildIdempotencyKey = (action) => [action, props.workId || 'work', props.chapterId || 'chapter', Date.now()].join(':')

const loadCandidateDrafts = async () => {
  if (!canOperate.value) return
  const payload = unwrapData(await aiApi.listCandidateDrafts({ work_id: props.workId, chapter_id: props.chapterId }))
  candidateDrafts.value = payload.items || []
}

const loadCandidateDetail = async (candidateDraftId) => {
  const [draftPayload, versionsPayload] = await Promise.all([
    aiApi.getCandidateDraft(candidateDraftId),
    aiApi.listCandidateDraftVersions(candidateDraftId)
  ])
  const detail = unwrapData(draftPayload)
  const versions = unwrapData(versionsPayload).items || []
  candidateDetails.value = { ...candidateDetails.value, [candidateDraftId]: detail }
  candidateVersions.value = { ...candidateVersions.value, [candidateDraftId]: versions }
  selectedVersionByDraft.value = {
    ...selectedVersionByDraft.value,
    [candidateDraftId]: detail.selected_version_id || versions[0]?.candidate_version_id || ''
  }
}

const loadAISuggestions = async () => {
  if (!canOperate.value) return
  const payload = unwrapData(await aiApi.listAISuggestions({ work_id: props.workId, chapter_id: props.chapterId }))
  aiSuggestions.value = payload.items || []
}

const loadMemoryGates = async () => {
  if (!canOperate.value) return
  const payload = unwrapData(await aiApi.listMemoryGates({ work_id: props.workId, chapter_id: props.chapterId }))
  memoryGates.value = payload.items || []
}

const loadConflicts = async () => {
  if (!canOperate.value) return
  const payload = unwrapData(await aiApi.listConflicts({ work_id: props.workId, chapter_id: props.chapterId }))
  conflicts.value = payload.items || []
}

const loadAgentTraces = async () => {
  if (!canOperate.value) return
  const payload = unwrapData(await aiApi.listAgentTraces({ work_id: props.workId, chapter_id: props.chapterId }))
  agentTraces.value = payload.items || []
}

const refreshReviewWorkspace = async () => {
  await Promise.all([loadCandidateDrafts(), loadAISuggestions(), loadMemoryGates(), loadConflicts(), loadAgentTraces()])
}

const selectedVersionIdOf = (candidateDraftId) => {
  return selectedVersionByDraft.value[candidateDraftId] || candidateDetails.value[candidateDraftId]?.selected_version_id || ''
}

const handleStartContinuation = async () => {
  candidateActionError.value = ''
  try {
    continuationResult.value = unwrapData(await aiApi.startContinuation({
      work_id: props.workId,
      chapter_id: props.chapterId,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('candidate_start')
    }))
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '生成候选稿失败，请稍后重试。')
  }
}

const handleAcceptCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.acceptCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      candidate_version_id: selectedVersionIdOf(candidateDraftId),
      idempotency_key: buildIdempotencyKey('candidate_accept')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿接受失败，请稍后重试。')
  }
}

const handleRejectCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      candidate_version_id: selectedVersionIdOf(candidateDraftId),
      reason: 'manual reject',
      idempotency_key: buildIdempotencyKey('candidate_reject')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿拒绝失败，请稍后重试。')
  }
}

const handleApplyCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    const draftConflicts = conflictsByDraft.value[candidateDraftId] || []
    if (draftConflicts.some((item) => item.severity === 'blocking')) {
      candidateActionError.value = '存在阻断冲突，处理完成后才能应用。'
      return
    }
    const warnings = draftConflicts.filter((item) => item.severity === 'warning')
    if (warnings.length) {
      const confirmed = window.confirm(`当前有 ${warnings.length} 条风险提示，继续应用代表你已知晓风险。是否继续？`)
      if (!confirmed) return
    }
    await aiApi.applyCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      candidate_version_id: selectedVersionIdOf(candidateDraftId),
      expected_chapter_version: props.chapterVersion,
      idempotency_key: buildIdempotencyKey('candidate_apply')
    })
    ElMessage.success('候选稿已应用到正文。')
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿应用失败，请稍后重试。')
  }
}

const handleReviewCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.reviewCandidateDraft(candidateDraftId, { user_instruction: '' }))
    let reviewDetail = payload
    if (payload.review_id) {
      reviewDetail = unwrapData(await aiApi.getAIReview(payload.review_id))
    }
    candidateReviewByDraft.value = { ...candidateReviewByDraft.value, [candidateDraftId]: reviewDetail }
    await loadAISuggestions()
    await loadMemoryGates()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'AI 审阅失败，请稍后重试。')
  }
}

const handleCandidateVersionDetail = async (candidateDraftId, candidateVersionId) => {
  const payload = unwrapData(await aiApi.getCandidateDraftVersion(candidateDraftId, candidateVersionId))
  candidateVersionDetails.value = { ...candidateVersionDetails.value, [candidateVersionId]: payload }
}

const handleSelectCandidateVersion = async (candidateDraftId, candidateVersionId) => {
  candidateActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.selectCandidateDraftVersion(candidateDraftId, candidateVersionId, {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('candidate_select')
    }))
    selectedVersionByDraft.value = { ...selectedVersionByDraft.value, [candidateDraftId]: candidateVersionId }
    candidateDetails.value = { ...candidateDetails.value, [candidateDraftId]: payload }
    await loadCandidateDrafts()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '候选版本切换失败，请稍后重试。')
  }
}

const handleCandidateVersionDiff = async (candidateDraftId, fromVersionId, toVersionId) => {
  const payload = unwrapData(await aiApi.getCandidateDraftVersionDiff(candidateDraftId, {
    from_version_id: fromVersionId,
    to_version_id: toVersionId
  }))
  candidateVersionDiffs.value = { ...candidateVersionDiffs.value, [candidateDraftId]: payload }
}

const handleRewriteCandidate = async (candidateDraftId, candidateVersionId, triggerType) => {
  candidateActionError.value = ''
  try {
    const userInstruction = triggerType === 'user_instruction'
      ? window.prompt('请输入本次重写要求', '请强化关键线索与人物动机。')
      : ''
    if (triggerType === 'user_instruction' && userInstruction === null) return
    await aiApi.rewriteCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      source_version_id: candidateVersionId,
      trigger_type: triggerType,
      review_report_id: candidateReviewByDraft.value[candidateDraftId]?.review_id || '',
      user_instruction: triggerType === 'user_instruction' ? String(userInstruction || '').trim() : '',
      idempotency_key: buildIdempotencyKey('candidate_rewrite')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿修订失败，请稍后重试。')
  }
}

const handleRejectCandidateVersion = async (candidateDraftId, candidateVersionId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraftVersion(candidateDraftId, candidateVersionId, {
      caller_type: 'user_action',
      user_action: true,
      reason: 'manual reject current version',
      idempotency_key: buildIdempotencyKey('candidate_version_reject')
    })
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '候选版本拒绝失败，请稍后重试。')
  }
}

const handleSuggestionDetail = async (suggestionId) => {
  const payload = unwrapData(await aiApi.getAISuggestion(suggestionId))
  aiSuggestionDetails.value = { ...aiSuggestionDetails.value, [suggestionId]: payload }
}

const handleAcceptSuggestion = async (suggestionId) => {
  await aiApi.acceptAISuggestion(suggestionId, {
    caller_type: 'user_action',
    user_action: true,
    idempotency_key: buildIdempotencyKey('suggestion_accept')
  })
  await loadAISuggestions()
}

const handleDismissSuggestion = async (suggestionId) => {
  await aiApi.dismissAISuggestion(suggestionId, {
    caller_type: 'user_action',
    user_action: true,
    decision_note: 'manual dismiss',
    idempotency_key: buildIdempotencyKey('suggestion_dismiss')
  })
  await loadAISuggestions()
}

const handleConvertSuggestion = async (suggestionId) => {
  const payload = unwrapData(await aiApi.convertAISuggestion(suggestionId, {
    caller_type: 'user_action',
    user_action: true,
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

const handleConflictDetail = async (recordId) => {
  const payload = unwrapData(await aiApi.getConflict(recordId))
  conflictDetails.value = { ...conflictDetails.value, [recordId]: payload }
}

const handleConflictDecision = async (recordId, decision, decisionNote = '') => {
  await aiApi.decideConflict(recordId, {
    caller_type: 'user_action',
    user_action: true,
    decision,
    decision_note: decisionNote || 'manual acknowledge',
    idempotency_key: buildIdempotencyKey('conflict_decide')
  })
  await loadConflicts()
}

const handleApproveMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.approveMemorySuggestion(gateId, suggestionId, {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('memory_approve')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议审批失败，请稍后重试。')
  }
}

const handleEditApproveMemorySuggestion = async (gateId, suggestion) => {
  memoryActionError.value = ''
  try {
    const editedValue = window.prompt('请输入修改后的摘要', suggestion.proposed_value_summary || '')
    if (editedValue === null) return
    await aiApi.editApproveMemorySuggestion(gateId, suggestion.id, {
      caller_type: 'user_action',
      user_action: true,
      decision_note: 'manual edit approve',
      proposed_value_summary: editedValue,
      idempotency_key: buildIdempotencyKey('memory_edit_approve')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议编辑审批失败，请稍后重试。')
  }
}

const handleRejectMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.rejectMemorySuggestion(gateId, suggestionId, {
      caller_type: 'user_action',
      user_action: true,
      decision_note: 'manual reject',
      idempotency_key: buildIdempotencyKey('memory_reject')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议拒绝失败，请稍后重试。')
  }
}

const handleDeferMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.deferMemorySuggestion(gateId, suggestionId, {
      caller_type: 'user_action',
      user_action: true,
      decision_note: 'manual defer',
      idempotency_key: buildIdempotencyKey('memory_defer')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议暂缓失败，请稍后重试。')
  }
}

const handleApplyMemoryGate = async (gateId) => {
  memoryActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.applyMemoryGate(gateId, {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('memory_apply')
    }))
    for (const revisionId of payload.revision_ids || []) {
      await handleMemoryRevisionDetail(revisionId)
    }
    await loadMemoryGates()
    ElMessage.success('记忆修订已应用。')
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆修订应用失败。')
  }
}

const handleMemoryRevisionDetail = async (revisionId) => {
  const payload = unwrapData(await aiApi.getMemoryRevision(revisionId))
  memoryRevisionDetails.value = { ...memoryRevisionDetails.value, [revisionId]: payload }
}

const handleRollbackMemoryRevision = async (revisionId) => {
  memoryActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.rollbackMemoryRevision(revisionId, {
      caller_type: 'user_action',
      user_action: true,
      decision_note: 'manual rollback',
      idempotency_key: buildIdempotencyKey('memory_rollback')
    }))
    memoryRevisionDetails.value = { ...memoryRevisionDetails.value, [payload.revision_id]: payload }
    await loadMemoryGates()
    ElMessage.success('记忆修订已回滚。')
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆修订回滚失败。')
  }
}

const handleTraceSteps = async (traceId) => {
  traceActionError.value = ''
  try {
    await aiApi.getAgentTrace(traceId)
    const payload = unwrapData(await aiApi.getAgentTraceSteps(traceId))
    agentTraceSteps.value = { ...agentTraceSteps.value, [traceId]: payload.items || [] }
  } catch (error) {
    traceActionError.value = String(error?.userMessage || error?.message || '任务步骤加载失败，请稍后重试。')
  }
}

const handleTraceDetail = async (traceId) => {
  traceActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.getAgentTraceDetailView(traceId, {
      detail: true,
      developer_mode: props.developerMode
    }))
    agentTraceDetails.value = { ...agentTraceDetails.value, [traceId]: payload }
  } catch (error) {
    traceActionError.value = String(error?.userMessage || error?.message || '任务详细追踪加载失败，请稍后重试。')
  }
}

watch(
  () => [props.workId, props.chapterId],
  async () => {
    if (!canOperate.value) return
    await refreshReviewWorkspace()
  },
  { immediate: true }
)
</script>

<style scoped>
.review-tab {
  --review-bg: var(--studio-card-bg, var(--ink-surface-1));
  --review-bg-soft: var(--studio-bg-focus, var(--ink-surface-2));
  --review-border: var(--studio-border, var(--ink-border));
  --review-title: var(--studio-title, var(--ink-text-primary));
  --review-text: var(--studio-text, var(--ink-text-secondary));
  --review-warning-bg: var(--ink-warning-bg);
  --review-warning-text: var(--ink-warning-text);
  --review-danger-bg: var(--ink-danger-bg);
  --review-danger-text: var(--ink-danger-text);
  display: grid;
  gap: 16px;
  min-height: 0;
}

.review-header,
.review-section {
  border: 1px solid var(--review-border);
  border-radius: 20px;
  background: var(--review-bg);
  padding: 18px;
}

.review-header h3,
.section-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--review-title);
}

.review-header p,
.section-header p,
.entity-summary span,
.detail-meta,
.note-box,
.empty-state {
  color: var(--review-text);
}

.review-header p,
.section-header p {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.entity-list,
.nested-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.entity-card,
.nested-card {
  border: 1px solid var(--review-border);
  border-radius: 16px;
  background: var(--review-bg-soft);
  padding: 14px;
}

.entity-summary,
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
}

.entity-summary strong {
  color: var(--review-title);
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.action-row button,
.primary-button {
  border: 1px solid var(--review-border);
  border-radius: 999px;
  background: var(--review-bg);
  color: var(--review-text);
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.primary-button {
  border-color: var(--ink-accent);
  background: var(--ink-accent);
  color: #fff;
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.detail-block {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}

.detail-pre,
.note-box {
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--review-border);
  border-radius: 14px;
  background: var(--review-bg);
  padding: 12px 14px;
}

.status-banner {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid var(--review-border);
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 12px;
}

.status-banner--warning {
  background: var(--review-warning-bg);
  color: var(--review-warning-text);
}

.status-banner--blocking {
  background: var(--review-danger-bg);
  color: var(--review-danger-text);
}

.gate-actions {
  margin-top: 10px;
}

.empty-state {
  font-size: 13px;
}

.error-text {
  margin-top: 10px;
  color: var(--review-danger-text);
  font-size: 13px;
}
</style>
