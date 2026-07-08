<template>
  <section class="review-tab" data-panel="review">
    <header class="review-header">
      <div>
        <h3>{{ text.reviewWorkspace }}</h3>
        <p>{{ text.reviewWorkspaceDesc }}</p>
      </div>
    </header>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>{{ text.candidateSection }}</h4>
          <p>{{ text.candidateSectionDesc }}</p>
        </div>
        <button
          type="button"
          class="ink-button ink-button--primary primary-button"
          data-test="candidate-start-continuation"
          :disabled="!canOperate"
          @click="handleStartContinuation"
        >
          {{ text.startCandidate }}
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
        <strong>{{ conflictSummary.blockingCount ? text.blockingConflictTitle : text.warningConflictTitle }}</strong>
        <span v-if="conflictSummary.blockingCount">
          {{ text.blockingConflictMessage(conflictSummary.blockingCount) }}
        </span>
        <span v-else>
          {{ text.warningConflictMessage(conflictSummary.warningCount) }}
        </span>
      </div>

      <ul v-if="candidateDrafts.length" class="entity-list">
        <li v-for="item in candidateDrafts" :key="item.candidate_draft_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ item.candidate_draft_id }}</strong>
            <span>{{ displayStatus(item.status) }}</span>
            <span>{{ displayValidationStatus(item.validation_status) }}</span>
            <span>{{ item.content_preview || text.noPreview }}</span>
            <span v-if="selectedVersionByDraft[item.candidate_draft_id]">
              {{ text.currentVersion }} {{ selectedVersionByDraft[item.candidate_draft_id] }}
            </span>
            <span v-if="item.accepted_version_id">{{ text.acceptedVersion }} {{ item.accepted_version_id }}</span>
            <span v-if="item.applied_version_id">{{ text.appliedVersion }} {{ item.applied_version_id }}</span>
          </div>

          <div class="action-row">
            <button
              type="button"
              :data-test="`candidate-detail-${item.candidate_draft_id}`"
              @click="handleCandidateDetail(item.candidate_draft_id)"
            >
              {{ text.viewDetail }}
            </button>
            <button
              type="button"
              :data-test="`candidate-accept-${item.candidate_draft_id}`"
              @click="handleAcceptCandidate(item.candidate_draft_id)"
            >
              {{ text.acceptCurrentVersion }}
            </button>
            <button
              type="button"
              :data-test="`candidate-reject-${item.candidate_draft_id}`"
              @click="handleRejectCandidate(item.candidate_draft_id)"
            >
              {{ text.rejectCurrentVersion }}
            </button>
            <button
              type="button"
              :data-test="`candidate-apply-${item.candidate_draft_id}`"
              @click="handleApplyCandidate(item.candidate_draft_id)"
            >
              {{ text.applyToDraft }}
            </button>
            <button
              type="button"
              :data-test="`candidate-review-${item.candidate_draft_id}`"
              @click="handleReviewCandidate(item.candidate_draft_id)"
            >
              {{ text.aiReview }}
            </button>
          </div>

          <div v-if="candidateDetails[item.candidate_draft_id]" class="note-box">
            <strong>{{ text.candidateDetail }}</strong>
            <pre>{{ candidateDetails[item.candidate_draft_id].content || candidateDetails[item.candidate_draft_id].content_preview || text.noPreview }}</pre>
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
                <span>{{ version.content_summary || text.noSummary }}</span>
              </div>

              <div class="action-row">
                <button
                  type="button"
                  :data-test="`candidate-version-detail-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  @click="handleCandidateVersionDetail(item.candidate_draft_id, version.candidate_version_id)"
                >
                  {{ text.viewVersion }}
                </button>
                <button
                  type="button"
                  :data-test="`candidate-version-select-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  @click="handleSelectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                >
                  {{ text.selectVersion }}
                </button>
                <button
                  v-if="index > 0"
                  type="button"
                  :data-test="`candidate-version-diff-${item.candidate_draft_id}-${candidateVersions[item.candidate_draft_id][index - 1].candidate_version_id}-${version.candidate_version_id}`"
                  @click="handleCandidateVersionDiff(item.candidate_draft_id, candidateVersions[item.candidate_draft_id][index - 1].candidate_version_id, version.candidate_version_id)"
                >
                  {{ text.viewDiff }}
                </button>
                <button
                  type="button"
                  :data-test="`candidate-version-rewrite-review-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'review_based')"
                >
                  {{ text.rewriteByReview }}
                </button>
                <button
                  type="button"
                  :data-test="`candidate-version-rewrite-user-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'user_instruction')"
                >
                  {{ text.rewriteByInstruction }}
                </button>
                <button
                  type="button"
                  :data-test="`candidate-version-reject-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  @click="handleRejectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                >
                  {{ text.rejectThisVersion }}
                </button>
              </div>

              <pre v-if="candidateVersionDetails[version.candidate_version_id]" class="detail-pre">{{
                candidateVersionDetails[version.candidate_version_id].content || candidateVersionDetails[version.candidate_version_id].content_summary || text.noPreview
              }}</pre>
            </li>
          </ul>

          <div v-if="candidateReviewByDraft[item.candidate_draft_id]" class="note-box">
            {{ candidateReviewByDraft[item.candidate_draft_id].summary }}
          </div>
          <div v-if="candidateVersionDiffs[item.candidate_draft_id]" class="note-box">
            {{ candidateVersionDiffs[item.candidate_draft_id].summary }}
          </div>

          <ul v-if="conflictsByDraft[item.candidate_draft_id]?.length" class="nested-list">
            <li
              v-for="conflict in conflictsByDraft[item.candidate_draft_id]"
              :key="conflict.record_id"
              class="nested-card"
            >
              <div class="entity-summary">
                <strong>{{ conflict.title }}</strong>
                <span>{{ displayConflictType(conflict.conflict_type) }}</span>
                <span>{{ displaySeverity(conflict.severity) }}</span>
                <span>{{ conflict.summary }}</span>
              </div>
              <div class="action-row">
                <button
                  type="button"
                  :data-test="`conflict-detail-${conflict.record_id}`"
                  @click="handleConflictDetail(conflict.record_id)"
                >
                  {{ text.viewConflict }}
                </button>
                <button
                  type="button"
                  :data-test="`conflict-ack-${conflict.record_id}`"
                  @click="handleConflictDecision(conflict.record_id, 'acknowledged', 'manual acknowledge')"
                >
                  {{ text.acknowledge }}
                </button>
                <button
                  v-if="conflict.severity !== 'blocking'"
                  type="button"
                  :data-test="`conflict-dismiss-${conflict.record_id}`"
                  @click="handleConflictDecision(conflict.record_id, 'dismissed', 'manual defer')"
                >
                  {{ text.defer }}
                </button>
              </div>
              <div v-if="conflictDetails[conflict.record_id]" class="note-box">
                {{ conflictDetails[conflict.record_id].summary }}
              </div>
            </li>
          </ul>
        </li>
      </ul>
      <div v-else class="empty-state">{{ text.emptyCandidates }}</div>
    </section>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>{{ text.suggestionSection }}</h4>
          <p>{{ text.suggestionSectionDesc }}</p>
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
            <button
              type="button"
              :data-test="`suggestion-detail-${item.suggestion_id}`"
              @click="handleSuggestionDetail(item.suggestion_id)"
            >
              {{ text.viewSuggestion }}
            </button>
            <button
              type="button"
              :data-test="`suggestion-accept-${item.suggestion_id}`"
              @click="handleAcceptSuggestion(item.suggestion_id)"
            >
              {{ text.acceptSuggestion }}
            </button>
            <button
              type="button"
              :data-test="`suggestion-dismiss-${item.suggestion_id}`"
              @click="handleDismissSuggestion(item.suggestion_id)"
            >
              {{ text.dismissSuggestion }}
            </button>
            <button
              v-if="item.suggestion_type !== 'risk_warning'"
              type="button"
              :data-test="`suggestion-convert-${item.suggestion_id}`"
              @click="handleConvertSuggestion(item.suggestion_id)"
            >
              {{ text.convertSuggestion }}
            </button>
          </div>
          <div v-if="aiSuggestionDetails[item.suggestion_id]" class="note-box">
            {{ aiSuggestionDetails[item.suggestion_id].summary }}
          </div>
        </li>
      </ul>
      <div v-else class="empty-state">{{ text.emptySuggestions }}</div>
    </section>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>{{ text.memorySection }}</h4>
          <p>{{ text.memorySectionDesc }}</p>
        </div>
      </div>
      <ul v-if="memoryGates.length" class="entity-list">
        <li v-for="gate in memoryGates" :key="gate.gate_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ gate.gate_id }}</strong>
            <span>{{ displayStatus(gate.state) }}</span>
            <span>{{ text.suggestionCount }} {{ (gate.suggestions || []).length }}</span>
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
                <button
                  type="button"
                  :data-test="`memory-approve-${gate.gate_id}-${suggestion.id}`"
                  @click="handleApproveMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  {{ text.memoryApprove }}
                </button>
                <button
                  type="button"
                  :data-test="`memory-edit-approve-${gate.gate_id}-${suggestion.id}`"
                  @click="handleEditApproveMemorySuggestion(gate.gate_id, suggestion)"
                >
                  {{ text.memoryEditApprove }}
                </button>
                <button
                  type="button"
                  :data-test="`memory-reject-${gate.gate_id}-${suggestion.id}`"
                  @click="handleRejectMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  {{ text.memoryReject }}
                </button>
                <button
                  type="button"
                  :data-test="`memory-defer-${gate.gate_id}-${suggestion.id}`"
                  @click="handleDeferMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  {{ text.defer }}
                </button>
              </div>
            </li>
          </ul>

          <div class="action-row gate-actions">
            <button
              type="button"
              :data-test="`memory-apply-${gate.gate_id}`"
              @click="handleApplyMemoryGate(gate.gate_id)"
            >
              {{ text.applyMemoryGate }}
            </button>
          </div>

          <ul v-if="gate.revision_ids?.length" class="nested-list">
            <li v-for="revisionId in gate.revision_ids" :key="revisionId" class="nested-card">
              <div class="entity-summary">
                <strong>{{ revisionId }}</strong>
                <span>{{ displayStatus(memoryRevisionDetails[revisionId]?.status || 'revision') }}</span>
              </div>
              <div class="action-row">
                <button
                  type="button"
                  :data-test="`memory-revision-detail-${revisionId}`"
                  @click="handleMemoryRevisionDetail(revisionId)"
                >
                  {{ text.viewMemoryRevision }}
                </button>
                <button
                  v-if="memoryRevisionDetails[revisionId]?.status === 'applied'"
                  type="button"
                  :data-test="`memory-revision-rollback-${revisionId}`"
                  @click="handleRollbackMemoryRevision(revisionId)"
                >
                  {{ text.rollbackMemoryRevision }}
                </button>
              </div>
              <div v-if="memoryRevisionDetails[revisionId]" class="note-box">
                {{ memoryRevisionDetails[revisionId].summary || text.memoryRevisionLoaded }}
              </div>
            </li>
          </ul>
        </li>
      </ul>
      <div v-else class="empty-state">{{ text.emptyMemory }}</div>
    </section>

    <section class="review-section">
      <div class="section-header">
        <div>
          <h4>{{ text.traceSection }}</h4>
          <p>{{ text.traceSectionDesc }}</p>
        </div>
      </div>
      <ul v-if="agentTraces.length" class="entity-list">
        <li v-for="trace in agentTraces" :key="trace.trace_id" class="entity-card">
          <div class="entity-summary">
            <strong>{{ trace.trace_id }}</strong>
            <span>{{ displayWorkflowType(trace.workflow_type) }}</span>
            <span>{{ displayStatus(trace.status) }}</span>
            <span>{{ text.stepCount }} {{ trace.total_steps || 0 }}</span>
          </div>
          <div class="action-row">
            <button
              type="button"
              :data-test="`trace-steps-${trace.trace_id}`"
              @click="handleTraceSteps(trace.trace_id)"
            >
              {{ text.viewTraceSteps }}
            </button>
            <button
              v-if="developerMode"
              type="button"
              :data-test="`trace-detail-${trace.trace_id}`"
              @click="handleTraceDetail(trace.trace_id)"
            >
              {{ text.viewTraceDetail }}
            </button>
          </div>
          <ul v-if="agentTraceSteps[trace.trace_id]?.length" class="nested-list">
            <li
              v-for="step in agentTraceSteps[trace.trace_id]"
              :key="step.step_id"
              class="nested-card"
            >
              <div class="entity-summary">
                <strong>{{ step.step_id }}</strong>
                <span>{{ displayAgentType(step.agent_type) }}</span>
                <span>{{ displayStepAction(step.action) }}</span>
                <span>{{ displayStatus(step.status) }}</span>
              </div>
            </li>
          </ul>
          <div v-if="agentTraceDetails[trace.trace_id]" class="note-box">
            {{ agentTraceDetails[trace.trace_id].summary || text.traceDetailLoaded }}
          </div>
        </li>
      </ul>
      <div v-else class="empty-state">{{ text.emptyTrace }}</div>
    </section>

    <div v-if="candidateActionError" class="error-banner">{{ candidateActionError }}</div>
    <div v-if="memoryActionError" class="error-banner">{{ memoryActionError }}</div>
    <div v-if="traceActionError" class="error-banner">{{ traceActionError }}</div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { aiApi } from '@/api'

const props = defineProps({
  workId: { type: String, default: '' },
  chapterId: { type: String, default: '' },
  chapterVersion: { type: Number, default: 0 },
  developerMode: { type: Boolean, default: false }
})

const text = {
  reviewWorkspace: '\u5ba1\u9605\u5de5\u4f5c\u533a',
  reviewWorkspaceDesc: '\u5019\u9009\u7a3f\u3001AI \u5efa\u8bae\u3001\u51b2\u7a81\u63d0\u793a\u3001\u8bb0\u5fc6\u5ba1\u6279\u4e0e\u4efb\u52a1\u8ffd\u8e2a\u90fd\u5728\u8fd9\u91cc\u96c6\u4e2d\u5904\u7406\u3002',
  candidateSection: '\u5019\u9009\u7a3f\u4e0e\u4eba\u5de5\u786e\u8ba4\u95e8',
  candidateSectionDesc: '\u6240\u6709 AI \u751f\u6210\u5185\u5bb9\u90fd\u4f1a\u5148\u8fdb\u5165\u5019\u9009\u7a3f\uff0c\u53ea\u6709\u660e\u786e\u7684\u7528\u6237\u64cd\u4f5c\u624d\u80fd\u63a5\u53d7\u3001\u62d2\u7edd\u6216\u5e94\u7528\u5230\u6b63\u6587\u3002',
  startCandidate: '\u751f\u6210\u5019\u9009\u7a3f',
  blockingConflictTitle: '\u5b58\u5728\u963b\u65ad\u51b2\u7a81',
  warningConflictTitle: '\u5b58\u5728\u98ce\u9669\u63d0\u793a',
  blockingConflictMessage: (count) => `\u5f53\u524d\u6709 ${count} \u6761\u963b\u65ad\u51b2\u7a81\uff0c\u5904\u7406\u5b8c\u6210\u540e\u624d\u80fd\u5e94\u7528\u5230\u6b63\u6587\u3002`,
  warningConflictMessage: (count) => `\u5f53\u524d\u6709 ${count} \u6761\u98ce\u9669\u63d0\u793a\uff0c\u7ee7\u7eed\u5e94\u7528\u4ee3\u8868\u4f60\u5df2\u77e5\u6653\u98ce\u9669\u3002`,
  noPreview: '\u6682\u65e0\u9884\u89c8',
  noSummary: '\u6682\u65e0\u6458\u8981',
  currentVersion: '\u5f53\u524d\u7248\u672c',
  acceptedVersion: '\u5df2\u63a5\u53d7',
  appliedVersion: '\u5df2\u5e94\u7528',
  viewDetail: '\u67e5\u770b\u8be6\u60c5',
  acceptCurrentVersion: '\u63a5\u53d7\u5f53\u524d\u7248\u672c',
  rejectCurrentVersion: '\u62d2\u7edd\u5f53\u524d\u7248\u672c',
  applyToDraft: '\u5e94\u7528\u5230\u6b63\u6587',
  aiReview: 'AI \u5ba1\u9605',
  candidateDetail: '\u5019\u9009\u8be6\u60c5',
  viewVersion: '\u67e5\u770b\u7248\u672c',
  selectVersion: '\u9009\u62e9\u7248\u672c',
  viewDiff: '\u67e5\u770b\u5dee\u5f02',
  rewriteByReview: '\u6309\u5ba1\u9605\u610f\u89c1\u4fee\u8ba2',
  rewriteByInstruction: '\u8f93\u5165\u8981\u6c42\u540e\u91cd\u5199',
  rejectThisVersion: '\u62d2\u7edd\u6b64\u7248\u672c',
  viewConflict: '\u67e5\u770b\u51b2\u7a81',
  acknowledge: '\u6211\u5df2\u77e5\u6653',
  defer: '\u7a0d\u540e\u5904\u7406',
  emptyCandidates: '\u5f53\u524d\u7ae0\u8282\u8fd8\u6ca1\u6709\u5019\u9009\u7a3f\u3002',
  suggestionSection: 'AI \u5efa\u8bae',
  suggestionSectionDesc: 'AI \u53ea\u7ed9\u51fa\u5efa\u8bae\uff0c\u4e0d\u4f1a\u81ea\u52a8\u6267\u884c\u3002\u4f60\u786e\u8ba4\u4e4b\u540e\uff0c\u5b83\u624d\u4f1a\u8f6c\u6210\u540e\u7eed\u52a8\u4f5c\u3002',
  viewSuggestion: '\u67e5\u770b\u5efa\u8bae',
  acceptSuggestion: '\u91c7\u7eb3\u5efa\u8bae',
  dismissSuggestion: '\u5ffd\u7565\u5efa\u8bae',
  convertSuggestion: '\u8f6c\u4e3a\u540e\u7eed\u52a8\u4f5c',
  emptySuggestions: '\u5f53\u524d\u6ca1\u6709\u5f85\u5904\u7406\u7684 AI \u5efa\u8bae\u3002',
  memorySection: '\u8bb0\u5fc6\u5ba1\u6279',
  memorySectionDesc: '\u8bb0\u5fc6\u66f4\u65b0\u4e0d\u4f1a\u81ea\u52a8\u5199\u5165\uff0c\u5fc5\u987b\u7ecf\u8fc7\u72ec\u7acb\u5ba1\u6279\u540e\u624d\u80fd\u5e94\u7528\u5230\u6b63\u5f0f\u8bb0\u5fc6\u3002',
  suggestionCount: '\u5efa\u8bae\u6570',
  memoryApprove: '\u5ba1\u6279\u901a\u8fc7',
  memoryEditApprove: '\u4fee\u6539\u540e\u901a\u8fc7',
  memoryReject: '\u62d2\u7edd\u5efa\u8bae',
  applyMemoryGate: '\u5e94\u7528\u672c\u7ec4\u4fee\u8ba2',
  viewMemoryRevision: '\u67e5\u770b\u4fee\u8ba2\u8be6\u60c5',
  rollbackMemoryRevision: '\u6267\u884c\u56de\u6eda',
  memoryRevisionLoaded: '\u8be6\u7ec6\u4fee\u8ba2\u5df2\u52a0\u8f7d\u3002',
  emptyMemory: '\u5f53\u524d\u6ca1\u6709\u5f85\u5ba1\u6279\u7684\u8bb0\u5fc6\u66f4\u65b0\u3002',
  traceSection: '\u4efb\u52a1\u8ffd\u8e2a',
  traceSectionDesc: '\u666e\u901a\u7528\u6237\u9ed8\u8ba4\u53ea\u770b\u6458\u8981\uff0c\u8be6\u7ec6\u8ffd\u8e2a\u53ea\u5728\u5f00\u53d1\u8005\u6a21\u5f0f\u4e0b\u5c55\u793a\u3002',
  stepCount: '\u6b65\u9aa4\u6570',
  viewTraceSteps: '\u67e5\u770b\u6b65\u9aa4',
  viewTraceDetail: '\u67e5\u770b\u8be6\u7ec6\u8ffd\u8e2a',
  traceDetailLoaded: '\u8be6\u7ec6\u8ffd\u8e2a\u5df2\u52a0\u8f7d\u3002',
  emptyTrace: '\u5f53\u524d\u6ca1\u6709\u4efb\u52a1\u8ffd\u8e2a\u8bb0\u5f55\u3002',
  errorStartCandidate: '\u751f\u6210\u5019\u9009\u7a3f\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorCandidateAccept: '\u5019\u9009\u7a3f\u63a5\u53d7\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorCandidateReject: '\u5019\u9009\u7a3f\u62d2\u7edd\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorCandidateApplyBlocked: '\u5b58\u5728\u963b\u65ad\u51b2\u7a81\uff0c\u5904\u7406\u5b8c\u6210\u540e\u624d\u80fd\u5e94\u7528\u3002',
  confirmCandidateApply: (count) => `\u5f53\u524d\u6709 ${count} \u6761\u98ce\u9669\u63d0\u793a\uff0c\u7ee7\u7eed\u5e94\u7528\u4ee3\u8868\u4f60\u5df2\u77e5\u6653\u98ce\u9669\u3002\u662f\u5426\u7ee7\u7eed\uff1f`,
  successCandidateApply: '\u5019\u9009\u7a3f\u5df2\u5e94\u7528\u5230\u6b63\u6587\u3002',
  errorCandidateApply: '\u5019\u9009\u7a3f\u5e94\u7528\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorCandidateReview: 'AI \u5ba1\u9605\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorVersionSelect: '\u5019\u9009\u7248\u672c\u5207\u6362\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  promptRewriteTitle: '\u8bf7\u8f93\u5165\u672c\u6b21\u91cd\u5199\u8981\u6c42',
  promptRewriteDefault: '\u8bf7\u5f3a\u5316\u5173\u952e\u4fe1\u606f\u4e0e\u4eba\u7269\u52a8\u673a\u3002',
  errorCandidateRewrite: '\u5019\u9009\u7a3f\u4fee\u8ba2\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorVersionReject: '\u5019\u9009\u7248\u672c\u62d2\u7edd\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorMemoryApprove: '\u8bb0\u5fc6\u5efa\u8bae\u5ba1\u6279\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  promptMemorySummaryTitle: '\u8bf7\u8f93\u5165\u4fee\u6539\u540e\u7684\u6458\u8981',
  errorMemoryEditApprove: '\u8bb0\u5fc6\u5efa\u8bae\u7f16\u8f91\u5ba1\u6279\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorMemoryReject: '\u8bb0\u5fc6\u5efa\u8bae\u62d2\u7edd\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorMemoryDefer: '\u8bb0\u5fc6\u5efa\u8bae\u6682\u7f13\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  successMemoryApply: '\u8bb0\u5fc6\u4fee\u8ba2\u5df2\u5e94\u7528\u3002',
  errorMemoryApply: '\u8bb0\u5fc6\u4fee\u8ba2\u5e94\u7528\u5931\u8d25\u3002',
  successMemoryRollback: '\u8bb0\u5fc6\u4fee\u8ba2\u5df2\u56de\u6eda\u3002',
  errorMemoryRollback: '\u8bb0\u5fc6\u4fee\u8ba2\u56de\u6eda\u5931\u8d25\u3002',
  errorTraceSteps: '\u4efb\u52a1\u6b65\u9aa4\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002',
  errorTraceDetail: '\u4efb\u52a1\u8be6\u7ec6\u8ffd\u8e2a\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
}

const canOperate = computed(() => Boolean(props.workId && props.chapterId))

const candidateDrafts = ref([])
const candidateDetails = reactive({})
const candidateVersions = reactive({})
const candidateVersionDetails = reactive({})
const candidateVersionDiffs = reactive({})
const selectedVersionByDraft = reactive({})
const candidateReviewByDraft = reactive({})
const aiSuggestions = ref([])
const aiSuggestionDetails = reactive({})
const conflicts = ref([])
const conflictDetails = reactive({})
const memoryGates = ref([])
const memoryRevisionDetails = reactive({})
const agentTraces = ref([])
const agentTraceSteps = reactive({})
const agentTraceDetails = reactive({})
const candidateActionError = ref('')
const memoryActionError = ref('')
const traceActionError = ref('')

const statusLabels = {
  pending: '\u5f85\u5f00\u59cb',
  generated: '\u5df2\u751f\u6210',
  shown: '\u5df2\u5c55\u793a',
  accepted: '\u5df2\u63a5\u53d7',
  rejected: '\u5df2\u62d2\u7edd',
  applied: '\u5df2\u5e94\u7528',
  review_completed: '\u5ba1\u9605\u5b8c\u6210',
  reviewing: '\u5ba1\u9605\u4e2d',
  waiting_for_user: '\u7b49\u5f85\u7528\u6237',
  completed: '\u5df2\u5b8c\u6210',
  completed_with_candidate: '\u5df2\u751f\u6210\u5019\u9009\u7a3f',
  running: '\u8fdb\u884c\u4e2d',
  revision_requested: '\u5df2\u8bf7\u6c42\u4fee\u8ba2',
  superseded: '\u5df2\u6709\u65b0\u7248\u672c',
  stale: '\u53ef\u80fd\u5df2\u8fc7\u671f',
  failed: '\u5931\u8d25',
  acknowledged: '\u5df2\u77e5\u6653',
  dismissed: '\u5df2\u5ffd\u7565',
  converted: '\u5df2\u8f6c\u4e3a\u540e\u7eed\u52a8\u4f5c',
  waiting_for_review: '\u7b49\u5f85\u5ba1\u6279',
  approved: '\u5ba1\u6279\u901a\u8fc7',
  detail: '\u5df2\u52a0\u8f7d\u8be6\u60c5',
  revision: '\u4fee\u8ba2\u8bb0\u5f55'
}

const validationStatusLabels = {
  passed: '\u6821\u9a8c\u901a\u8fc7',
  failed: '\u6821\u9a8c\u5931\u8d25',
  warning: '\u5b58\u5728\u98ce\u9669',
  skipped: '\u672a\u6821\u9a8c'
}

const suggestionTypeLabels = {
  rewrite_suggestion: '\u6539\u5199\u5efa\u8bae',
  style_suggestion: '\u98ce\u683c\u5efa\u8bae',
  plot_suggestion: '\u5267\u60c5\u5efa\u8bae',
  character_suggestion: '\u4eba\u7269\u5efa\u8bae',
  foreshadow_suggestion: '\u4f0f\u7b14\u5efa\u8bae',
  memory_update_suggestion_ref: '\u8bb0\u5fc6\u66f4\u65b0\u5efa\u8bae',
  conflict_resolution_suggestion: '\u51b2\u7a81\u5904\u7406\u5efa\u8bae',
  direction_plan_suggestion: '\u65b9\u5411\u4e0e\u8ba1\u5212\u5efa\u8bae',
  continuity_suggestion: '\u8fde\u7eed\u6027\u5efa\u8bae',
  risk_warning: '\u98ce\u9669\u63d0\u793a'
}

const severityLabels = {
  low: '\u4f4e',
  medium: '\u4e2d',
  high: '\u9ad8',
  critical: '\u5173\u952e',
  info: '\u63d0\u793a',
  warning: '\u8b66\u544a',
  blocking: '\u963b\u65ad'
}

const conflictTypeLabels = {
  candidate_version_conflict: '\u5019\u9009\u7248\u672c\u51b2\u7a81',
  character_conflict: '\u4eba\u7269\u51b2\u7a81',
  setting_conflict: '\u8bbe\u5b9a\u51b2\u7a81',
  timeline_conflict: '\u65f6\u95f4\u7ebf\u51b2\u7a81',
  arc_conflict: '\u5267\u60c5\u8f68\u9053\u51b2\u7a81',
  direction_plan_conflict: '\u65b9\u5411\u8ba1\u5212\u51b2\u7a81',
  memory_conflict: '\u8bb0\u5fc6\u51b2\u7a81',
  foreshadow_conflict: '\u4f0f\u7b14\u51b2\u7a81',
  user_draft_conflict: '\u6b63\u6587\u8349\u7a3f\u51b2\u7a81',
  apply_version_conflict: '\u5e94\u7528\u7248\u672c\u51b2\u7a81',
  unknown_conflict: '\u672a\u5f52\u7c7b\u51b2\u7a81'
}

const workflowTypeLabels = {
  continuation: '\u7eed\u5199\u4efb\u52a1',
  rewrite: '\u4fee\u8ba2\u4efb\u52a1',
  review: '\u5ba1\u9605\u4efb\u52a1',
  planning: '\u89c4\u5212\u4efb\u52a1'
}

const agentTypeLabels = {
  memory: '\u7406\u89e3\u6545\u4e8b',
  planner: '\u89c4\u5212\u65b9\u5411',
  writer: '\u751f\u6210\u5019\u9009\u7a3f',
  reviewer: '\u5ba1\u9605\u7a3f\u4ef6',
  rewriter: '\u4fee\u8ba2\u7a3f\u4ef6'
}

const stepActionLabels = {
  review: '\u6267\u884c\u5ba1\u9605',
  draft: '\u751f\u6210\u5019\u9009\u7a3f',
  rewrite: '\u6267\u884c\u4fee\u8ba2',
  planning: '\u89c4\u5212\u4efb\u52a1',
  analysis: '\u5206\u6790\u4e0a\u4e0b\u6587'
}

const memoryTargetLabels = {
  character: '\u4eba\u7269\u8bb0\u5fc6',
  setting: '\u8bbe\u5b9a\u8bb0\u5fc6',
  timeline: '\u65f6\u95f4\u7ebf\u8bb0\u5fc6',
  foreshadow: '\u4f0f\u7b14\u8bb0\u5fc6',
  plot_thread: '\u5267\u60c5\u7ebf\u7d22',
  story_state: '\u7ae0\u8282\u72b6\u6001',
  continuity_note: '\u8fde\u7eed\u6027\u5907\u6ce8'
}

const revisionTypeLabels = {
  character_update: '\u4eba\u7269\u66f4\u65b0',
  setting_update: '\u8bbe\u5b9a\u66f4\u65b0',
  timeline_event_add: '\u65b0\u589e\u65f6\u95f4\u7ebf\u4e8b\u4ef6',
  timeline_event_update: '\u66f4\u65b0\u65f6\u95f4\u7ebf\u4e8b\u4ef6',
  foreshadow_add: '\u65b0\u589e\u4f0f\u7b14',
  foreshadow_update: '\u63a8\u8fdb\u4f0f\u7b14',
  foreshadow_resolve: '\u56de\u6536\u4f0f\u7b14',
  plot_thread_update: '\u5267\u60c5\u7ebf\u7d22\u66f4\u65b0',
  story_state_update: '\u7ae0\u8282\u72b6\u6001\u66f4\u65b0',
  arc_note_update: '\u8f68\u9053\u5907\u6ce8\u66f4\u65b0',
  continuity_note_add: '\u8fde\u7eed\u6027\u5907\u6ce8',
  unknown_memory_update: '\u672a\u5f52\u7c7b\u8bb0\u5fc6\u66f4\u65b0'
}

const unwrapData = (payload) => payload?.data ?? payload ?? {}

const displayStatus = (value) => statusLabels[String(value || '')] || String(value || '\u672a\u77e5')
const displayValidationStatus = (value) => validationStatusLabels[String(value || '')] || String(value || '\u672a\u6821\u9a8c')
const displaySuggestionType = (value) => suggestionTypeLabels[String(value || '')] || String(value || '\u672a\u77e5\u5efa\u8bae')
const displaySeverity = (value) => severityLabels[String(value || '')] || String(value || '\u672a\u77e5\u7b49\u7ea7')
const displayConflictType = (value) => conflictTypeLabels[String(value || '')] || String(value || '\u672a\u5f52\u7c7b\u51b2\u7a81')
const displayWorkflowType = (value) => workflowTypeLabels[String(value || '')] || String(value || '\u672a\u77e5\u4efb\u52a1')
const displayAgentType = (value) => agentTypeLabels[String(value || '')] || String(value || '\u672a\u77e5\u89d2\u8272')
const displayStepAction = (value) => stepActionLabels[String(value || '')] || String(value || '\u672a\u77e5\u52a8\u4f5c')
const displayMemoryTargetType = (value) => memoryTargetLabels[String(value || '')] || String(value || '\u672a\u77e5\u8bb0\u5fc6')
const displayRevisionType = (value) => revisionTypeLabels[String(value || '')] || String(value || '\u672a\u77e5\u4fee\u8ba2')

const conflictsByDraft = computed(() => {
  const grouped = {}
  for (const item of conflicts.value) {
    const draftId = String(item?.candidate_draft_id || '')
    if (!draftId) continue
    if (!grouped[draftId]) grouped[draftId] = []
    grouped[draftId].push(item)
  }
  return grouped
})

const conflictSummary = computed(() => {
  const blockingCount = conflicts.value.filter((item) => String(item?.severity || '') === 'blocking').length
  const warningCount = conflicts.value.filter((item) => String(item?.severity || '') === 'warning').length
  return { blockingCount, warningCount }
})

const buildIdempotencyKey = (action) => `${action}_${props.workId}_${props.chapterId}_${Date.now()}`

const userActionPayload = (action, extra = {}) => ({
  caller_type: 'user_action',
  user_action: true,
  idempotency_key: buildIdempotencyKey(action),
  ...extra
})

const loadCandidateDrafts = async () => {
  if (!canOperate.value) {
    candidateDrafts.value = []
    return
  }
  const payload = unwrapData(await aiApi.listCandidateDrafts({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  const items = Array.isArray(payload.items) ? payload.items : []
  candidateDrafts.value = items
  for (const item of items) {
    selectedVersionByDraft[item.candidate_draft_id] = item.selected_version_id || ''
  }
}

const loadAISuggestions = async () => {
  if (!canOperate.value) {
    aiSuggestions.value = []
    return
  }
  const payload = unwrapData(await aiApi.listAISuggestions({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  aiSuggestions.value = Array.isArray(payload.items) ? payload.items : []
}

const loadConflicts = async () => {
  if (!canOperate.value) {
    conflicts.value = []
    return
  }
  const payload = unwrapData(await aiApi.listConflicts({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  conflicts.value = Array.isArray(payload.items) ? payload.items : []
}

const loadMemoryGates = async () => {
  if (!canOperate.value) {
    memoryGates.value = []
    return
  }
  const payload = unwrapData(await aiApi.listMemoryGates({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  memoryGates.value = Array.isArray(payload.items) ? payload.items : []
}

const loadAgentTraces = async () => {
  if (!canOperate.value) {
    agentTraces.value = []
    return
  }
  const payload = unwrapData(await aiApi.listAgentTraces({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  agentTraces.value = Array.isArray(payload.items) ? payload.items : []
}

const loadAll = async () => {
  candidateActionError.value = ''
  memoryActionError.value = ''
  traceActionError.value = ''
  if (!canOperate.value) return
  await Promise.all([
    loadCandidateDrafts(),
    loadAISuggestions(),
    loadConflicts(),
    loadMemoryGates(),
    loadAgentTraces()
  ])
}

const getSelectedVersionId = (candidateDraftId) => {
  const detail = candidateDetails[candidateDraftId]
  const item = candidateDrafts.value.find((draft) => draft.candidate_draft_id === candidateDraftId)
  return selectedVersionByDraft[candidateDraftId] || detail?.selected_version_id || item?.selected_version_id || ''
}

const handleStartContinuation = async () => {
  candidateActionError.value = ''
  try {
    await aiApi.startContinuation({
      work_id: props.workId,
      chapter_id: props.chapterId,
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('candidate_start_continuation')
    })
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = text.errorStartCandidate
    ElMessage.error(candidateActionError.value)
  }
}

const handleCandidateDetail = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.getCandidateDraft(candidateDraftId))
    candidateDetails[candidateDraftId] = payload
    if (payload.selected_version_id) {
      selectedVersionByDraft[candidateDraftId] = payload.selected_version_id
    }
    const versionsPayload = unwrapData(await aiApi.listCandidateDraftVersions(candidateDraftId))
    candidateVersions[candidateDraftId] = Array.isArray(versionsPayload.items) ? versionsPayload.items : []
  } catch (error) {
    candidateActionError.value = '\u5019\u9009\u7a3f\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleAcceptCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.acceptCandidateDraft(candidateDraftId, userActionPayload('accept_candidate', {
      candidate_version_id: getSelectedVersionId(candidateDraftId)
    }))
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = text.errorCandidateAccept
    ElMessage.error(candidateActionError.value)
  }
}

const handleRejectCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraft(candidateDraftId, userActionPayload('reject_candidate', {
      candidate_version_id: getSelectedVersionId(candidateDraftId)
    }))
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = text.errorCandidateReject
    ElMessage.error(candidateActionError.value)
  }
}

const handleApplyCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  const draftConflicts = conflictsByDraft.value[candidateDraftId] || []
  const blocking = draftConflicts.filter((item) => item.severity === 'blocking')
  if (blocking.length) {
    candidateActionError.value = text.errorCandidateApplyBlocked
    ElMessage.error(candidateActionError.value)
    return
  }
  const warnings = draftConflicts.filter((item) => item.severity === 'warning')
  if (warnings.length) {
    const confirmed = window.confirm(text.confirmCandidateApply(warnings.length))
    if (!confirmed) return
  }
  try {
    await aiApi.applyCandidateDraft(candidateDraftId, userActionPayload('apply_candidate', {
      expected_chapter_version: Number(props.chapterVersion || 0)
    }))
    ElMessage.success(text.successCandidateApply)
    await loadCandidateDrafts()
  } catch (error) {
    candidateActionError.value = text.errorCandidateApply
    ElMessage.error(candidateActionError.value)
  }
}

const handleReviewCandidate = async (candidateDraftId) => {
  candidateActionError.value = ''
  try {
    const reviewPayload = unwrapData(await aiApi.reviewCandidateDraft(candidateDraftId, {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('candidate_review')
    }))
    let detail = reviewPayload
    if (reviewPayload.review_id) {
      detail = unwrapData(await aiApi.getAIReview(reviewPayload.review_id))
    }
    candidateReviewByDraft[candidateDraftId] = detail
  } catch (error) {
    candidateActionError.value = text.errorCandidateReview
    ElMessage.error(candidateActionError.value)
  }
}

const handleCandidateVersionDetail = async (candidateDraftId, versionId) => {
  candidateActionError.value = ''
  try {
    candidateVersionDetails[versionId] = unwrapData(await aiApi.getCandidateDraftVersion(candidateDraftId, versionId))
  } catch (error) {
    candidateActionError.value = '\u5019\u9009\u7248\u672c\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleSelectCandidateVersion = async (candidateDraftId, versionId) => {
  candidateActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.selectCandidateDraftVersion(
      candidateDraftId,
      versionId,
      userActionPayload('select_candidate_version')
    ))
    selectedVersionByDraft[candidateDraftId] = payload.selected_version_id || versionId
    candidateDetails[candidateDraftId] = {
      ...(candidateDetails[candidateDraftId] || {}),
      ...payload
    }
  } catch (error) {
    candidateActionError.value = text.errorVersionSelect
    ElMessage.error(candidateActionError.value)
  }
}

const handleCandidateVersionDiff = async (candidateDraftId, fromVersionId, toVersionId) => {
  candidateActionError.value = ''
  try {
    candidateVersionDiffs[candidateDraftId] = unwrapData(await aiApi.getCandidateDraftVersionDiff(candidateDraftId, {
      from_version_id: fromVersionId,
      to_version_id: toVersionId
    }))
  } catch (error) {
    candidateActionError.value = '\u5019\u9009\u7248\u672c\u5dee\u5f02\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleRewriteCandidate = async (candidateDraftId, versionId, triggerType) => {
  candidateActionError.value = ''
  try {
    const payload = {
      source_version_id: versionId,
      trigger_type: triggerType,
      caller_type: 'user_action'
    }
    if (triggerType === 'user_instruction') {
      const instruction = window.prompt(text.promptRewriteTitle, text.promptRewriteDefault)
      if (instruction == null) return
      payload.instruction = String(instruction || '').trim()
    }
    await aiApi.rewriteCandidateDraft(candidateDraftId, payload)
    await handleCandidateDetail(candidateDraftId)
  } catch (error) {
    candidateActionError.value = text.errorCandidateRewrite
    ElMessage.error(candidateActionError.value)
  }
}

const handleRejectCandidateVersion = async (candidateDraftId, versionId) => {
  candidateActionError.value = ''
  try {
    await aiApi.rejectCandidateDraftVersion(
      candidateDraftId,
      versionId,
      userActionPayload('reject_candidate_version')
    )
    await handleCandidateDetail(candidateDraftId)
  } catch (error) {
    candidateActionError.value = text.errorVersionReject
    ElMessage.error(candidateActionError.value)
  }
}

const handleSuggestionDetail = async (suggestionId) => {
  candidateActionError.value = ''
  try {
    aiSuggestionDetails[suggestionId] = unwrapData(await aiApi.getAISuggestion(suggestionId))
  } catch (error) {
    candidateActionError.value = '\u5efa\u8bae\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleAcceptSuggestion = async (suggestionId) => {
  candidateActionError.value = ''
  try {
    await aiApi.acceptAISuggestion(suggestionId, userActionPayload('accept_suggestion'))
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = '\u5efa\u8bae\u91c7\u7eb3\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleDismissSuggestion = async (suggestionId) => {
  candidateActionError.value = ''
  try {
    await aiApi.dismissAISuggestion(suggestionId, userActionPayload('dismiss_suggestion'))
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = '\u5efa\u8bae\u5ffd\u7565\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleConvertSuggestion = async (suggestionId) => {
  candidateActionError.value = ''
  try {
    await aiApi.convertAISuggestion(suggestionId, userActionPayload('convert_suggestion'))
    await loadAISuggestions()
  } catch (error) {
    candidateActionError.value = '\u5efa\u8bae\u8f6c\u5316\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleConflictDetail = async (recordId) => {
  candidateActionError.value = ''
  try {
    conflictDetails[recordId] = unwrapData(await aiApi.getConflict(recordId))
  } catch (error) {
    candidateActionError.value = '\u51b2\u7a81\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleConflictDecision = async (recordId, decision, note) => {
  candidateActionError.value = ''
  try {
    await aiApi.decideConflict(recordId, userActionPayload('resolve_conflict', {
      decision,
      note
    }))
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = '\u51b2\u7a81\u5904\u7406\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(candidateActionError.value)
  }
}

const handleApproveMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.approveMemorySuggestion(gateId, suggestionId, userActionPayload('approve_memory'))
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = text.errorMemoryApprove
    ElMessage.error(memoryActionError.value)
  }
}

const handleEditApproveMemorySuggestion = async (gateId, suggestion) => {
  memoryActionError.value = ''
  const nextSummary = window.prompt(text.promptMemorySummaryTitle, suggestion?.proposed_value_summary || '')
  if (nextSummary == null) return
  try {
    await aiApi.editApproveMemorySuggestion(gateId, suggestion.id, userActionPayload('edit_approve_memory', {
      proposed_value_summary: String(nextSummary || '').trim()
    }))
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = text.errorMemoryEditApprove
    ElMessage.error(memoryActionError.value)
  }
}

const handleRejectMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.rejectMemorySuggestion(gateId, suggestionId, userActionPayload('reject_memory'))
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = text.errorMemoryReject
    ElMessage.error(memoryActionError.value)
  }
}

const handleDeferMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.deferMemorySuggestion(gateId, suggestionId, userActionPayload('defer_memory'))
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = text.errorMemoryDefer
    ElMessage.error(memoryActionError.value)
  }
}

const handleApplyMemoryGate = async (gateId) => {
  memoryActionError.value = ''
  try {
    await aiApi.applyMemoryGate(gateId, userActionPayload('apply_memory'))
    ElMessage.success(text.successMemoryApply)
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = text.errorMemoryApply
    ElMessage.error(memoryActionError.value)
  }
}

const handleMemoryRevisionDetail = async (revisionId) => {
  memoryActionError.value = ''
  try {
    memoryRevisionDetails[revisionId] = unwrapData(await aiApi.getMemoryRevision(revisionId))
  } catch (error) {
    memoryActionError.value = '\u8bb0\u5fc6\u4fee\u8ba2\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002'
    ElMessage.error(memoryActionError.value)
  }
}

const handleRollbackMemoryRevision = async (revisionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.rollbackMemoryRevision(revisionId, userActionPayload('rollback_memory'))
    ElMessage.success(text.successMemoryRollback)
    await handleMemoryRevisionDetail(revisionId)
  } catch (error) {
    memoryActionError.value = text.errorMemoryRollback
    ElMessage.error(memoryActionError.value)
  }
}

const handleTraceSteps = async (traceId) => {
  traceActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.getAgentTraceSteps(traceId))
    agentTraceSteps[traceId] = Array.isArray(payload.items) ? payload.items : []
  } catch (error) {
    traceActionError.value = text.errorTraceSteps
    ElMessage.error(traceActionError.value)
  }
}

const handleTraceDetail = async (traceId) => {
  traceActionError.value = ''
  try {
    agentTraceDetails[traceId] = unwrapData(await aiApi.getAgentTraceDetailView(traceId))
  } catch (error) {
    traceActionError.value = text.errorTraceDetail
    ElMessage.error(traceActionError.value)
  }
}

watch(
  () => [props.workId, props.chapterId],
  () => {
    loadAll()
  },
  { immediate: true }
)

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.review-tab {
  --review-surface: var(--workspace-panel-bg, var(--studio-card-bg, var(--ink-surface-1)));
  --review-surface-soft: var(--workspace-panel-bg-soft, var(--studio-bg-focus, var(--ink-surface-2)));
  --review-border: var(--workspace-panel-border, var(--studio-border, var(--ink-border)));
  --review-border-strong: var(--ink-border-strong);
  --review-title: var(--workspace-panel-title, var(--studio-title, var(--ink-text-primary)));
  --review-text: var(--workspace-panel-text, var(--studio-text, var(--ink-text-secondary)));
  --review-muted: var(--workspace-panel-muted, var(--studio-muted, var(--ink-text-muted)));

  display: grid;
  gap: 16px;
  color: var(--review-title);
}

.review-header,
.review-section {
  border: 1px solid var(--review-border);
  border-radius: 24px;
  background: var(--review-surface);
  padding: 20px;
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
.empty-state,
.note-box,
.error-banner {
  color: var(--review-text);
}

.review-header p,
.section-header p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.entity-list,
.nested-list {
  display: grid;
  gap: 12px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.entity-card,
.nested-card,
.note-box,
.status-banner {
  border: 1px solid var(--review-border);
  border-radius: 20px;
  background: var(--review-surface-soft);
  padding: 16px;
}

.entity-summary {
  display: grid;
  gap: 6px;
}

.entity-summary strong {
  color: var(--review-title);
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.action-row button,
.primary-button {
  min-width: 88px;
}

.action-row button {
  border: 1px solid var(--review-border-strong);
  border-radius: 999px;
  background: var(--review-surface);
  color: var(--review-title);
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.action-row button:disabled,
.primary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.detail-pre {
  margin: 14px 0 0;
  white-space: pre-wrap;
  color: var(--review-title);
  background: var(--review-surface);
  border: 1px solid var(--review-border);
  border-radius: 16px;
  padding: 12px;
}

.status-banner {
  display: grid;
  gap: 6px;
}

.status-banner--blocking {
  border-color: var(--ink-danger-border, #ef4444);
  background: var(--ink-danger-bg, rgba(239, 68, 68, 0.08));
}

.status-banner--warning {
  border-color: var(--ink-warning-border, #f59e0b);
  background: var(--ink-warning-bg, rgba(245, 158, 11, 0.08));
}

.empty-state,
.error-banner {
  padding: 12px 0;
}

.error-banner {
  border: 1px solid var(--ink-danger-border, #ef4444);
  border-radius: 18px;
  background: var(--ink-danger-bg, rgba(239, 68, 68, 0.08));
  padding: 14px 16px;
}
</style>
