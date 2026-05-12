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

    <div class="ai-section">
      <h4>续写与候选稿</h4>
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
          <div v-if="candidateReviewByDraft[item.candidate_draft_id]" class="ai-note">
            {{ candidateReviewByDraft[item.candidate_draft_id].summary }}
          </div>
        </li>
      </ul>
      <p v-if="candidateActionError" class="ai-error">{{ candidateActionError }}</p>
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
const candidateReviewByDraft = ref({})
const candidateActionError = ref('')
const quickTrialResult = ref({})
const polling = useAIJobPolling({ intervalMs: 1000 })

const quickTrialForm = reactive({
  input_text: '请试写一小段灯塔夜景。',
  model_role: 'quick_trial_writer'
})

const providerConfigs = computed(() => settings.value?.provider_configs || [])
const jobSteps = computed(() => polling.job.value?.steps || [])
const jobStatusText = computed(() => String(polling.job.value?.status || ''))
const initializationSummary = computed(() => ({
  analyzed: Number(initializationInfo.value?.analyzed_chapter_count || initializationInfo.value?.data?.analyzed_chapter_count || 0),
  empty: Number(initializationInfo.value?.empty_chapter_count || initializationInfo.value?.data?.empty_chapter_count || 0),
  failed: Number(initializationInfo.value?.failed_chapter_count || initializationInfo.value?.data?.failed_chapter_count || 0)
}))

const unwrapData = (payload) => payload?.data ?? payload ?? {}

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

const refreshPanel = async () => {
  await Promise.all([
    loadSettings(),
    loadInitialization(),
    loadContextReadiness(),
    loadCandidateDrafts()
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

const loadCandidateDetail = async (candidateDraftId) => {
  const payload = unwrapData(await aiApi.getCandidateDraft(candidateDraftId))
  candidateDetails.value = {
    ...candidateDetails.value,
    [candidateDraftId]: payload
  }
}

const handleAcceptCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.acceptCandidateDraft(candidateDraftId, { user_action: true, user_id: 'ui-user' })
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'accept failed')
  }
}

const handleRejectCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraft(candidateDraftId, { user_action: true, user_id: 'ui-user', reason: 'manual reject' })
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || 'reject failed')
  }
}

const handleApplyCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.applyCandidateDraft(candidateDraftId, {
      user_action: true,
      user_id: 'ui-user',
      expected_chapter_version: props.chapterVersion
    })
    ElMessage.success('apply 成功')
    await loadCandidateDrafts()
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
}

watch(() => props.workId, async () => {
  await refreshPanel()
}, { immediate: true })

watch(() => props.chapterId, async () => {
  await Promise.all([loadContextReadiness(), loadCandidateDrafts()])
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
