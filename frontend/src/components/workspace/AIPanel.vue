<template>
  <section class="ai-panel" data-test="ai-panel">
    <header class="ai-panel-header">
      <div>
        <h3>{{ panelTitle }}</h3>
        <p>{{ panelDescription }}</p>
      </div>
    </header>

    <div v-if="showAIMode" class="ai-section">
      <h4>AI 设置</h4>
      <div v-if="providerConfigs.length" class="ai-list ai-settings-list">
        <div
          v-for="provider in providerConfigs"
          :key="provider.provider_name"
          class="ai-settings-card"
        >
          <div class="candidate-summary">
            <strong>{{ provider.provider_name }}</strong>
            <span>{{ provider.enabled ? '已启用' : '已停用' }}</span>
            <span>模型 {{ provider.default_model || '未设置' }}</span>
            <span>Key {{ provider.key_configured ? '已配置' : '未配置' }}</span>
            <span v-if="provider.api_key_masked">{{ provider.api_key_masked }}</span>
          </div>
          <div class="field-grid ai-settings-fields">
            <label class="ai-field">
              <span>启用 Provider</span>
              <input
                :data-test="`ai-settings-provider-enabled-${provider.provider_name}`"
                v-model="provider.enabled"
                type="checkbox"
              />
            </label>
            <label class="ai-field">
              <span>默认模型</span>
              <input
                :data-test="`ai-settings-provider-model-${provider.provider_name}`"
                v-model="provider.default_model"
                type="text"
                placeholder="default model"
              />
            </label>
            <label class="ai-field">
              <span>API Key</span>
              <input
                :data-test="`ai-settings-provider-key-${provider.provider_name}`"
                v-model="provider.api_key"
                type="password"
                autocomplete="new-password"
                placeholder="输入新的 Provider Key"
              />
            </label>
            <label class="ai-field">
              <span>Base URL</span>
              <input
                :data-test="`ai-settings-provider-base-url-${provider.provider_name}`"
                v-model="provider.base_url"
                type="text"
                placeholder="可选 base_url"
              />
            </label>
            <label class="ai-field">
              <span>超时秒数</span>
              <input
                :data-test="`ai-settings-provider-timeout-${provider.provider_name}`"
                v-model.number="provider.timeout"
                type="number"
                min="1"
              />
            </label>
          </div>
          <div class="ai-meta">
            <span v-if="provider.last_test_status">测试 {{ provider.last_test_status }}</span>
            <span v-if="provider.last_test_error_message">{{ provider.last_test_error_message }}</span>
          </div>
        </div>
      </div>
      <div class="field-grid ai-settings-role-grid">
        <label v-for="role in requiredSettingsRoles" :key="role" class="ai-field">
          <span>{{ role }} 映射</span>
          <select
            :data-test="`ai-settings-role-provider-${role}`"
            v-model="settingsForm.model_role_mappings[role].provider_name"
          >
            <option value="">请选择 Provider</option>
            <option
              v-for="provider in providerConfigs"
              :key="`${role}-${provider.provider_name}`"
              :value="provider.provider_name"
            >
              {{ provider.provider_name }}
            </option>
          </select>
          <input
            :data-test="`ai-settings-role-${role}`"
            v-model="settingsForm.model_role_mappings[role].model_name"
            type="text"
            :placeholder="`${role} model`"
          />
        </label>
      </div>
      <div v-if="aiSettingsBlocked" class="settings-block-banner" data-test="ai-settings-blocked">
        <strong>AI 设置未完成</strong>
        <span>{{ aiSettingsBlockMessage }}</span>
      </div>
      <div class="ai-actions">
        <button data-test="ai-settings-save" type="button" @click="handleSaveSettings">保存配置</button>
        <button data-test="ai-test-provider" type="button" @click="handleTestProvider">测试 Provider</button>
      </div>
      <p v-if="settingsSaveMessage" class="ai-note">{{ settingsSaveMessage }}</p>
      <p v-if="settingsErrorMessage" class="ai-error">{{ settingsErrorMessage }}</p>
      <p v-if="providerTestMessage" class="ai-note">{{ providerTestMessage }}</p>
    </div>

    <div v-if="showAIMode" class="ai-section">
      <h4>初始化分析</h4>
      <div class="ai-actions">
        <button
          data-test="ai-start-initialization"
          type="button"
          :disabled="aiSettingsBlocked"
          @click="handleStartInitialization"
        >
          启动初始化
        </button>
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

    <div v-if="showAIMode" class="ai-section">
      <h4>ContextPack</h4>
      <div class="ai-actions">
        <button
          data-test="ai-build-context-pack"
          type="button"
          :disabled="aiSettingsBlocked"
          @click="handleBuildContextPack"
        >
          构建 ContextPack
        </button>
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

    <div v-if="showAIMode && plotArcVisible" class="ai-section">
      <h4>剧情轨道详情</h4>
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
      <ul v-if="plotArcs.length" class="ai-list">
        <li v-for="arc in plotArcs" :key="arc.arc_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ arc.title || arc.arc_id }}</strong>
            <span>{{ arc.arc_level }}</span>
            <span>{{ arc.status }}</span>
          </div>
          <p v-if="arc.summary" class="ai-note">{{ arc.summary }}</p>
          <div class="ai-actions">
            <button
              :data-test="`plot-arc-detail-${arc.arc_id}`"
              type="button"
              @click="handlePlotArcDetail(arc.arc_id)"
            >
              查看详情
            </button>
          </div>
          <ul v-if="plotArcDetails[arc.arc_id]?.key_points?.length" class="ai-list">
            <li v-for="point in plotArcDetails[arc.arc_id].key_points" :key="point">{{ point }}</li>
          </ul>
        </li>
      </ul>
    </div>

    <div v-if="showAIMode" class="ai-section">
      <h4>AgentSession</h4>
      <ul v-if="agentSessions.length" class="ai-list">
        <li v-for="session in agentSessions" :key="session.session_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ session.session_id }}</strong>
            <span>{{ session.status }}</span>
            <span>{{ session.workflow_type }}</span>
            <span>{{ session.current_agent_type || session.current_stage || '-' }}</span>
            <span v-if="session.progress_percent !== undefined">{{ session.progress_percent }}%</span>
          </div>
          <div class="ai-actions">
            <button
              :data-test="`agent-session-detail-${session.session_id}`"
              type="button"
              @click="handleAgentSessionDetail(session.session_id)"
            >
              查看详情
            </button>
            <button
              :data-test="`agent-session-pause-${session.session_id}`"
              type="button"
              @click="handleAgentSessionAction(session.session_id, 'pause')"
            >
              暂停
            </button>
            <button
              :data-test="`agent-session-resume-${session.session_id}`"
              type="button"
              @click="handleAgentSessionAction(session.session_id, 'resume')"
            >
              恢复
            </button>
            <button
              :data-test="`agent-session-cancel-${session.session_id}`"
              type="button"
              @click="handleAgentSessionAction(session.session_id, 'cancel')"
            >
              取消
            </button>
          </div>
          <div v-if="agentSessionDetails[session.session_id]" class="ai-meta">
            <span>{{ agentSessionDetails[session.session_id].status }}</span>
            <span>{{ agentSessionDetails[session.session_id].current_stage || '-' }}</span>
            <span>{{ agentSessionDetails[session.session_id].current_agent_type || '-' }}</span>
          </div>
        </li>
      </ul>
    </div>

    <div v-if="showAIMode" class="ai-section">
      <h4>方向推演</h4>
      <div class="ai-actions">
        <button
          data-test="ai-generate-directions"
          type="button"
          :disabled="aiSettingsBlocked"
          @click="handleGenerateDirections"
        >
          生成方向
        </button>
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
                  :disabled="aiSettingsBlocked"
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
              :disabled="aiSettingsBlocked"
              @click="handleGeneratePlan(proposal.direction_proposal_id)"
            >
              生成计划
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div v-if="showAIMode" class="ai-section">
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

    <div v-if="showAIMode" class="ai-section">
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

    <div v-if="showReviewMode" class="ai-section">
      <h4>续写与候选稿</h4>
      <div v-if="aiSettingsBlocked" class="settings-block-banner">
        <strong>AI 设置未完成</strong>
        <span>{{ aiSettingsBlockMessage }}</span>
      </div>
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
        <button
          data-test="ai-start-continuation"
          type="button"
          :disabled="aiSettingsBlocked"
          @click="handleStartContinuation"
        >
          生成候选稿
        </button>
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
            <button
              :data-test="`candidate-review-${item.candidate_draft_id}`"
              type="button"
              :disabled="aiSettingsBlocked"
              @click="handleReviewCandidate(item.candidate_draft_id)"
            >
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

    <div v-if="showReviewMode" class="ai-section">
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

    <div v-if="showReviewMode" class="ai-section">
      <h4>记忆审批</h4>
      <ul v-if="memoryGates.length" class="ai-list">
        <li v-for="gate in memoryGates" :key="gate.gate_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ gate.gate_id }}</strong>
            <span>{{ gate.state }}</span>
            <span>suggestions {{ (gate.suggestions || []).length }}</span>
          </div>
          <ul class="ai-list">
            <li v-for="suggestion in gate.suggestions || []" :key="suggestion.id" class="planning-item">
              <div class="candidate-summary">
                <strong>{{ suggestion.target_memory_type }}</strong>
                <span>{{ suggestion.revision_type }}</span>
                <span>{{ suggestion.status }}</span>
                <span>{{ suggestion.current_value_summary }}</span>
                <span>{{ suggestion.proposed_value_summary }}</span>
              </div>
              <div class="ai-actions">
                <button
                  :data-test="`memory-approve-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleApproveMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  approve
                </button>
                <button
                  :data-test="`memory-edit-approve-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleEditApproveMemorySuggestion(gate.gate_id, suggestion)"
                >
                  edit+approve
                </button>
                <button
                  :data-test="`memory-reject-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleRejectMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  reject
                </button>
                <button
                  :data-test="`memory-defer-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleDeferMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  defer
                </button>
              </div>
            </li>
          </ul>
          <div class="ai-actions">
            <button
              :data-test="`memory-apply-${gate.gate_id}`"
              type="button"
              @click="handleApplyMemoryGate(gate.gate_id)"
            >
              apply gate
            </button>
          </div>
          <ul v-if="gate.revision_ids?.length" class="ai-list">
            <li v-for="revisionId in gate.revision_ids" :key="revisionId">
              <div class="candidate-summary">
                <strong>{{ revisionId }}</strong>
                <span>{{ memoryRevisionDetails[revisionId]?.status || 'revision' }}</span>
              </div>
              <div class="ai-actions">
                <button
                  :data-test="`memory-revision-detail-${revisionId}`"
                  type="button"
                  @click="handleMemoryRevisionDetail(revisionId)"
                >
                  查看 revision
                </button>
                <button
                  v-if="memoryRevisionDetails[revisionId]?.status === 'applied'"
                  :data-test="`memory-revision-rollback-${revisionId}`"
                  type="button"
                  @click="handleRollbackMemoryRevision(revisionId)"
                >
                  rollback
                </button>
              </div>
              <div v-if="memoryRevisionDetails[revisionId]" class="ai-note">
                {{ memoryRevisionDetails[revisionId].before_summary }} -> {{ memoryRevisionDetails[revisionId].after_summary }}
              </div>
            </li>
          </ul>
        </li>
      </ul>
      <p v-if="memoryActionError" class="ai-error">{{ memoryActionError }}</p>
    </div>

    <div v-if="showReviewMode" class="ai-section">
      <h4>Agent Trace</h4>
      <ul v-if="agentTraces.length" class="ai-list">
        <li v-for="trace in agentTraces" :key="trace.trace_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ trace.trace_id }}</strong>
            <span>{{ trace.status }}</span>
            <span>{{ trace.workflow_type }}</span>
            <span>steps {{ trace.total_steps || 0 }}</span>
            <span>tokens {{ trace.total_tokens || 0 }}</span>
          </div>
          <div class="ai-actions">
            <button
              :data-test="`trace-steps-${trace.trace_id}`"
              type="button"
              @click="handleTraceSteps(trace.trace_id)"
            >
              查看步骤
            </button>
            <button
              v-if="developerMode"
              :data-test="`trace-detail-${trace.trace_id}`"
              type="button"
              @click="handleTraceDetail(trace.trace_id)"
            >
              查看 Detail
            </button>
          </div>
          <ul v-if="agentTraceSteps[trace.trace_id]?.length" class="ai-list">
            <li v-for="step in agentTraceSteps[trace.trace_id]" :key="step.step_id">
              {{ step.agent_type }} / {{ step.action }} / {{ step.status }}
            </li>
          </ul>
          <div v-if="agentTraceDetails[trace.trace_id]" class="ai-note">
            <div v-if="agentTraceDetails[trace.trace_id].tool_calls?.length">
              tool {{ agentTraceDetails[trace.trace_id].tool_calls[0].tool_name }} / {{ agentTraceDetails[trace.trace_id].tool_calls[0].permission_result }}
            </div>
            <div v-if="agentTraceDetails[trace.trace_id].events?.length">
              event {{ agentTraceDetails[trace.trace_id].events[0].event_type }}
            </div>
            <ul v-if="agentTraceDetails[trace.trace_id].metrics?.length" class="ai-list">
              <li v-for="metric in agentTraceDetails[trace.trace_id].metrics" :key="metric.metric_id">
                {{ metric.metric_name }} / {{ metric.metric_value }}
              </li>
            </ul>
            <ul v-if="agentTraceDetails[trace.trace_id].alerts?.length" class="ai-list">
              <li v-for="alert in agentTraceDetails[trace.trace_id].alerts" :key="alert.alert_id">
                {{ alert.alert_type }} / {{ alert.status }} / {{ alert.summary }}
              </li>
            </ul>
            <ul v-if="agentTraceDetails[trace.trace_id].user_decisions?.length" class="ai-list">
              <li v-for="decision in agentTraceDetails[trace.trace_id].user_decisions" :key="decision.decision_trace_id">
                {{ decision.decision_type }} / {{ decision.target_entity_type }} / {{ decision.target_entity_id }}
              </li>
            </ul>
          </div>
        </li>
      </ul>
      <p v-if="traceActionError" class="ai-error">{{ traceActionError }}</p>
    </div>

    <div v-if="showAIMode" class="ai-section">
      <h4>Quick Trial</h4>
      <div class="field-grid">
        <input v-model="quickTrialForm.input_text" type="text" placeholder="临时 prompt" />
        <input v-model="quickTrialForm.model_role" type="text" placeholder="model_role" />
      </div>
      <div class="ai-actions">
        <button
          data-test="quick-trial-run"
          type="button"
          :disabled="aiSettingsBlocked"
          @click="handleRunQuickTrial"
        >
          运行试跑
        </button>
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
  },
  developerMode: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'all'
  }
})

const REQUIRED_SETTINGS_ROLES = ['analysis', 'planning', 'writer', 'reviewer', 'rewriter']

const settings = ref({ provider_configs: [], model_role_mappings: {} })
const settingsForm = reactive({
  provider_configs: [],
  model_role_mappings: Object.fromEntries(
    REQUIRED_SETTINGS_ROLES.map((role) => [role, { provider_name: '', model_name: '' }])
  )
})
const settingsSaveMessage = ref('')
const settingsErrorMessage = ref('')
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
const memoryGates = ref([])
const memoryRevisionDetails = ref({})
const memoryActionError = ref('')
const agentSessions = ref([])
const agentSessionDetails = ref({})
const agentTraces = ref([])
const agentTraceSteps = ref({})
const agentTraceDetails = ref({})
const traceActionError = ref('')
const conflicts = ref([])
const conflictDetails = ref({})
const plotArcs = ref([])
const plotArcDetails = ref({})
const candidateActionError = ref('')
const directionProposals = ref([])
const chapterPlans = ref([])
const writingTasks = ref([])
const planningActionError = ref('')
const quickTrialResult = ref({})
const polling = useAIJobPolling({ intervalMs: 1000 })
const sessionPolling = useAIJobPolling({
  intervalMs: 2000,
  maxIntervalMs: 5000,
  fetchJob: (sessionId) => aiApi.getAgentSession(sessionId),
  terminalStatuses: new Set(['completed', 'failed', 'cancelled', 'waiting_for_user']),
  sse: {
    enabled: typeof import.meta !== 'undefined' && String(import.meta.env?.VITE_AI_SSE_ENABLED || 'false') === 'true',
    buildUrl: (sessionId) => `/api/v2/ai/sessions/${encodeURIComponent(sessionId)}/events`
  }
})

const quickTrialForm = reactive({
  input_text: '请试写一小段灯塔夜景。',
  model_role: 'quick_trial_writer'
})

const requiredSettingsRoles = REQUIRED_SETTINGS_ROLES
const providerConfigs = computed(() => settingsForm.provider_configs || [])
const showAIMode = computed(() => props.mode !== 'review')
const showReviewMode = computed(() => props.mode !== 'ai')
const panelTitle = computed(() => (
  props.mode === 'review' ? '审阅工作区' : props.mode === 'ai' ? 'AI 工作区' : 'AI 助手'
))
const panelDescription = computed(() => (
  props.mode === 'review'
    ? '候选稿、审阅、冲突、记忆门控与 Trace 在此集中处理。'
    : props.mode === 'ai'
      ? '设置、初始化、ContextPack、剧情轨道、方向计划、会话进度与 Quick Trial。'
      : '最小集成入口：设置、初始化、ContextPack、续写、Quick Trial、AIReview。'
))
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
const providerNameOptions = computed(() => providerConfigs.value.map((item) => item.provider_name).filter(Boolean))
const aiSettingsBlockMessage = computed(() => {
  const enabledProviders = providerConfigs.value.filter((provider) => provider.enabled)
  if (!enabledProviders.some((provider) => provider.key_configured || String(provider.api_key || '').trim())) {
    return '请先配置可用 Provider Key 与 analysis/writer 角色映射。'
  }
  const requiredRoles = ['analysis', 'writer']
  const missingCriticalRole = requiredRoles.some((role) => {
    const mapping = settingsForm.model_role_mappings[role]
    if (!mapping) return true
    if (!String(mapping.provider_name || '').trim() || !String(mapping.model_name || '').trim()) return true
    const provider = providerConfigs.value.find((item) => item.provider_name === mapping.provider_name)
    if (!provider || !provider.enabled) return true
    return !(provider.key_configured || String(provider.api_key || '').trim())
  })
  if (missingCriticalRole) {
    return '请先配置可用 Provider Key 与 analysis/writer 角色映射。'
  }
  return ''
})
const aiSettingsBlocked = computed(() => Boolean(aiSettingsBlockMessage.value))

const unwrapData = (payload) => payload?.data ?? payload ?? {}

const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

const resetSettingsForm = (payload) => {
  const nextSettings = payload || { provider_configs: [], model_role_mappings: {} }
  const nextProviders = Array.isArray(nextSettings.provider_configs)
    ? nextSettings.provider_configs.map((provider) => ({
      provider_name: provider.provider_name || '',
      enabled: provider.enabled !== false,
      default_model: provider.default_model || '',
      api_key: '',
      api_key_masked: provider.api_key_masked || '',
      key_configured: Boolean(provider.key_configured),
      timeout: Number(provider.timeout || 30),
      base_url: provider.base_url || '',
      last_test_status: provider.last_test_status || '',
      last_test_at: provider.last_test_at || '',
      last_test_error_code: provider.last_test_error_code || '',
      last_test_error_message: provider.last_test_error_message || ''
    }))
    : []
  settingsForm.provider_configs.splice(0, settingsForm.provider_configs.length, ...nextProviders)

  const nextMappings = {}
  for (const role of REQUIRED_SETTINGS_ROLES) {
    const current = nextSettings.model_role_mappings?.[role] || {}
    nextMappings[role] = {
      provider_name: current.provider_name || providerNameOptions.value[0] || '',
      model_name: current.model_name || ''
    }
  }
  for (const [role, mapping] of Object.entries(nextSettings.model_role_mappings || {})) {
    if (!nextMappings[role]) {
      nextMappings[role] = {
        provider_name: mapping?.provider_name || providerNameOptions.value[0] || '',
        model_name: mapping?.model_name || ''
      }
    }
  }
  for (const key of Object.keys(settingsForm.model_role_mappings)) {
    delete settingsForm.model_role_mappings[key]
  }
  Object.assign(settingsForm.model_role_mappings, nextMappings)
}

const loadSettings = async () => {
  settings.value = unwrapData(await aiApi.getAISettings())
  resetSettingsForm(settings.value)
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

const loadAgentSessions = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listAgentSessions({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  agentSessions.value = payload.items || []
  const activeSessionId = String(agentSessions.value[0]?.session_id || '')
  if (activeSessionId) {
    await sessionPolling.start(activeSessionId)
  } else {
    sessionPolling.stop()
  }
}

const loadPlotArcs = async () => {
  if (!props.workId) return
  const [itemsPayload, statusPayload] = await Promise.all([
    aiApi.listPlotArcs({ work_id: props.workId }),
    aiApi.getPlotArcStatus({ work_id: props.workId, chapter_id: props.chapterId })
  ])
  plotArcs.value = unwrapData(itemsPayload).items || []
  const statusItems = unwrapData(statusPayload).items || []
  if (statusItems.length) {
    contextPackReadiness.value = {
      ...contextPackReadiness.value,
      plot_arc_statuses: statusItems.reduce((acc, item) => {
        acc[item.arc_level] = { status: item.status }
        return acc
      }, {})
    }
  }
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

const loadMemoryGates = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listMemoryGates({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  memoryGates.value = payload.items || []
}

const loadConflicts = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listConflicts({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  conflicts.value = payload.items || []
}

const loadAgentTraces = async () => {
  if (!props.workId) return
  const payload = unwrapData(await aiApi.listAgentTraces({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  agentTraces.value = payload.items || []
}

const refreshPanel = async () => {
  await Promise.all([
    loadSettings(),
    loadInitialization(),
    loadContextReadiness(),
    loadAgentSessions(),
    loadPlotArcs(),
    loadCandidateDrafts(),
    loadPlanningData(),
    loadAISuggestions(),
    loadMemoryGates(),
    loadConflicts(),
    loadAgentTraces()
  ])
}

const ensureAISettingsReady = (targetRef) => {
  if (!aiSettingsBlocked.value) return true
  const message = aiSettingsBlockMessage.value
  if (targetRef) {
    targetRef.value = message
  } else {
    providerTestMessage.value = message
  }
  return false
}

const buildSettingsPayload = () => ({
  caller_type: 'user_action',
  user_action: true,
  idempotency_key: buildIdempotencyKey('settings_update'),
  provider_configs: providerConfigs.value.map((provider) => ({
    provider_name: provider.provider_name,
    enabled: provider.enabled,
    api_key: String(provider.api_key || '').trim(),
    default_model: String(provider.default_model || '').trim(),
    timeout: Number(provider.timeout || 30),
    base_url: String(provider.base_url || '').trim() || null
  })),
  model_role_mappings: Object.fromEntries(
    Object.entries(settingsForm.model_role_mappings).map(([role, mapping]) => [role, {
      provider_name: String(mapping.provider_name || '').trim(),
      model_name: String(mapping.model_name || '').trim()
    }])
  )
})

const handleSaveSettings = async () => {
  settingsSaveMessage.value = ''
  settingsErrorMessage.value = ''
  providerTestMessage.value = ''
  if (!providerConfigs.value.length) {
    settingsErrorMessage.value = '当前没有可配置的 Provider。'
    return
  }
  try {
    const payload = unwrapData(await aiApi.updateAISettings(buildSettingsPayload()))
    settings.value = payload
    resetSettingsForm(payload)
    settingsSaveMessage.value = 'AI Settings 已保存。'
  } catch (error) {
    settingsErrorMessage.value = String(error?.userMessage || error?.message || 'settings save failed')
  }
}

const handleTestProvider = async () => {
  providerTestMessage.value = ''
  settingsErrorMessage.value = ''
  const provider = providerConfigs.value[0]
  if (!provider) {
    settingsErrorMessage.value = '当前没有可测试的 Provider。'
    return
  }
  try {
    const payload = unwrapData(await aiApi.testProvider(provider.provider_name, {
      model_name: provider.default_model || 'fake-chat',
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('provider_test')
    }))
    provider.key_configured = true
    providerTestMessage.value = payload.message || payload.test_status || 'ok'
  } catch (error) {
    providerTestMessage.value = String(error?.userMessage || error?.message || 'provider test failed')
  }
}

const handleStartInitialization = async () => {
  if (!ensureAISettingsReady(planningActionError)) return
  const payload = unwrapData(await aiApi.startInitialization({ work_id: props.workId }))
  initializationInfo.value = payload
  if (payload.job_id) {
    await polling.start(payload.job_id)
  }
}

const handleAgentSessionDetail = async (sessionId) => {
  const payload = unwrapData(await aiApi.getAgentSession(sessionId))
  agentSessionDetails.value = {
    ...agentSessionDetails.value,
    [sessionId]: payload
  }
}

const handleAgentSessionAction = async (sessionId, action) => {
  const payload = {
    caller_type: 'user_action',
    user_action: true,
    user_id: 'ui-user',
    idempotency_key: buildIdempotencyKey(`session_${action}`)
  }
  if (action === 'pause') {
    await aiApi.pauseAgentSession(sessionId, payload)
  } else if (action === 'resume') {
    await aiApi.resumeAgentSession(sessionId, payload)
  } else if (action === 'cancel') {
    await aiApi.cancelAgentSession(sessionId, payload)
  }
  await loadAgentSessions()
  await handleAgentSessionDetail(sessionId)
}

const handlePlotArcDetail = async (arcId) => {
  const payload = unwrapData(await aiApi.getPlotArc(arcId))
  plotArcDetails.value = {
    ...plotArcDetails.value,
    [arcId]: payload
  }
}

const handleCancelJob = async () => {
  if (!polling.jobId.value) return
  await aiApi.cancelAIJob(polling.jobId.value, { reason: 'user_cancelled' })
  await polling.fetchOnce()
}

const handleBuildContextPack = async () => {
  if (!ensureAISettingsReady(planningActionError)) return
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
  if (!ensureAISettingsReady(candidateActionError)) return
  continuationResult.value = unwrapData(await aiApi.startContinuation({
    work_id: props.workId,
    chapter_id: props.chapterId
  }))
  await loadCandidateDrafts()
}

const handleGenerateDirections = async () => {
  planningActionError.value = ''
  if (!ensureAISettingsReady(planningActionError)) return
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
  if (!ensureAISettingsReady(planningActionError)) return
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
  if (!ensureAISettingsReady(planningActionError)) return
  quickTrialResult.value = unwrapData(await aiApi.runQuickTrial({
    model_role: quickTrialForm.model_role,
    input_text: quickTrialForm.input_text
  }))
}

const handleReviewCandidate = async (candidateDraftId) => {
  if (!ensureAISettingsReady(candidateActionError)) return
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
  await loadMemoryGates()
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

const handleApproveMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.approveMemorySuggestion(gateId, suggestionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      idempotency_key: buildIdempotencyKey('memory_approve')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || 'memory approve failed')
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
      user_id: 'ui-user',
      decision_note: 'manual edit approve',
      proposed_value_summary: editedValue,
      idempotency_key: buildIdempotencyKey('memory_edit_approve')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || 'memory edit approve failed')
  }
}

const handleRejectMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.rejectMemorySuggestion(gateId, suggestionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      decision_note: 'manual reject',
      idempotency_key: buildIdempotencyKey('memory_reject')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || 'memory reject failed')
  }
}

const handleDeferMemorySuggestion = async (gateId, suggestionId) => {
  memoryActionError.value = ''
  try {
    await aiApi.deferMemorySuggestion(gateId, suggestionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      decision_note: 'manual defer',
      idempotency_key: buildIdempotencyKey('memory_defer')
    })
    await loadMemoryGates()
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || 'memory defer failed')
  }
}

const handleApplyMemoryGate = async (gateId) => {
  memoryActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.applyMemoryGate(gateId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      idempotency_key: buildIdempotencyKey('memory_apply')
    }))
    for (const revisionId of payload.revision_ids || []) {
      await handleMemoryRevisionDetail(revisionId)
    }
    await loadMemoryGates()
    ElMessage.success('记忆修订 apply 成功')
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || 'memory apply failed')
  }
}

const handleMemoryRevisionDetail = async (revisionId) => {
  const payload = unwrapData(await aiApi.getMemoryRevision(revisionId))
  memoryRevisionDetails.value = {
    ...memoryRevisionDetails.value,
    [revisionId]: payload
  }
}

const handleRollbackMemoryRevision = async (revisionId) => {
  memoryActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.rollbackMemoryRevision(revisionId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      decision_note: 'manual rollback',
      idempotency_key: buildIdempotencyKey('memory_rollback')
    }))
    memoryRevisionDetails.value = {
      ...memoryRevisionDetails.value,
      [payload.revision_id]: payload
    }
    await loadMemoryGates()
    ElMessage.success('rollback 成功')
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || 'memory rollback failed')
  }
}

const handleTraceSteps = async (traceId) => {
  traceActionError.value = ''
  try {
    await aiApi.getAgentTrace(traceId)
    const payload = unwrapData(await aiApi.getAgentTraceSteps(traceId))
    agentTraceSteps.value = {
      ...agentTraceSteps.value,
      [traceId]: payload.items || []
    }
  } catch (error) {
    traceActionError.value = String(error?.userMessage || error?.message || 'trace steps load failed')
  }
}

const handleTraceDetail = async (traceId) => {
  traceActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.getAgentTraceDetailView(traceId, {
      detail: true,
      developer_mode: props.developerMode
    }))
    agentTraceDetails.value = {
      ...agentTraceDetails.value,
      [traceId]: payload
    }
  } catch (error) {
    traceActionError.value = String(error?.userMessage || error?.message || 'trace detail load failed')
  }
}

watch(() => props.workId, async () => {
  await refreshPanel()
}, { immediate: true })

watch(() => props.chapterId, async () => {
  await Promise.all([
    loadContextReadiness(),
    loadAgentSessions(),
    loadPlotArcs(),
    loadCandidateDrafts(),
    loadPlanningData(),
    loadAISuggestions(),
    loadMemoryGates(),
    loadConflicts(),
    loadAgentTraces()
  ])
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

.settings-block-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid #f59e0b;
  background: #fffbeb;
  color: #92400e;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
}

.ai-actions,
.ai-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-actions button,
.field-grid input,
.field-grid select {
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

.ai-settings-list,
.ai-settings-fields,
.ai-settings-role-grid {
  padding-left: 0;
}

.ai-settings-card {
  display: grid;
  gap: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 12px;
  background: #f8fafc;
}

.ai-field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: #374151;
}
</style>
