﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <section class="ai-panel" data-test="ai-panel">
    <header class="ai-panel-header">
      <div>
        <h3>{{ panelTitle }}</h3>
        <p>{{ panelDescription }}</p>
      </div>
    </header>

    <ReviewTab
      v-if="isReviewMode"
      :work-id="workId"
      :chapter-id="chapterId"
      :chapter-version="chapterVersion"
      :developer-mode="developerMode"
    />

    <template v-else>
      <div v-if="showAIMode" class="ai-section">
      <h4>使用前检查</h4>
      <div class="ai-meta">
        <span v-if="aiSettingsBlocked">模型配置未完成</span>
        <span v-else>模型配置已完成</span>
        <span>详细配置与模型服务商管理请前往“设置”页面</span>
      </div>
      <div v-if="aiSettingsBlocked" class="settings-block-banner" data-test="ai-settings-blocked">
        <strong>暂时无法启动 AI 工作</strong>
        <span>{{ aiSettingsBlockMessage }}</span>
      </div>
      <div class="ai-actions">
        <button data-test="go-settings-page" type="button" @click="goToSettingsPage">前往设置页面</button>
      </div>
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
        <span v-if="initializationInfo.initialization_id">初始化ID {{ initializationInfo.initialization_id }}</span>
        <span v-if="polling.jobId">任务 {{ polling.jobId }}</span>
        <span v-if="jobStatusText">{{ displayStatus(jobStatusText) }}</span>
        <span>分析成功 {{ initializationSummary.analyzed }}</span>
        <span>空章节 {{ initializationSummary.empty }}</span>
        <span>失败章节 {{ initializationSummary.failed }}</span>
      </div>
      <ul v-if="jobSteps.length" class="ai-list">
        <li v-for="step in jobSteps" :key="step.step_id">{{ step.step_name }} / {{ displayStatus(step.status) }}</li>
      </ul>
      <p v-if="polling.error" class="ai-error">{{ polling.error }}</p>
    </div>

    <div v-if="showAIMode" class="ai-section">
      <h4>写作上下文</h4>
      <div class="ai-actions">
        <button
          data-test="ai-build-context-pack"
          type="button"
          :disabled="aiSettingsBlocked"
          @click="handleBuildContextPack"
        >
          构建写作上下文
        </button>
      </div>
      <div class="ai-meta">
        <span>状态 {{ displayStatus(contextPackReadiness.status || 'unknown') }}</span>
        <span v-if="contextPackReadiness.blocked_reason">阻塞原因：{{ displayReadinessReason(contextPackReadiness.blocked_reason) }}</span>
        <span v-if="contextPackReadiness.degraded_reason">降级原因：{{ displayReadinessReason(contextPackReadiness.degraded_reason) }}</span>
      </div>
      <ul v-if="contextPackItems.length" class="ai-list">
        <li v-for="item in contextPackItems" :key="item.item_id || item.source_type">
          {{ displayContextItemType(item.source_type || item.item_type) }} / {{ item.content_text || item.summary || '摘要' }}
        </li>
      </ul>
    </div>

    <div v-if="showAIMode && styleDNAStore.featureEnabled" class="ai-section">
      <StyleDNAConfigPanel
        :feature-enabled="styleDNAStore.featureEnabled"
        :ai-settings-blocked="aiSettingsBlocked"
        :loading="styleDNAStore.loading"
        :extracting="styleDNAStore.extracting"
        :extract-job-active="styleDNAStore.extractJobActive"
        :draft-text="styleDNADraftText"
        :source-mode="styleDNASourceMode"
        :chapter-options="styleDNAChapterOptions"
        :selected-chapter-ids="styleDNASelectedChapterIds"
        :active-profile="styleDNAStore.activeProfile"
        :current-profile="styleDNAStore.currentProfile"
        :history-profiles="styleDNAStore.historyProfiles"
        :warning-message="styleDNAStore.warningMessage"
        :error-message="styleDNAStore.errorMessage"
        @update:draft-text="styleDNADraftText = $event"
        @update:source-mode="styleDNASourceMode = $event"
        @update:selected-chapter-ids="styleDNASelectedChapterIds = $event"
        @extract="handleStyleDNAExtract"
        @confirm-profile="handleStyleDNAConfirm"
        @disable-profile="handleStyleDNADisable"
        @delete-profile="handleStyleDNADelete"
        @view-profile="handleStyleDNAViewProfile"
        @refresh="handleStyleDNARefresh"
      />
    </div>

    <div v-if="showAIMode && aiHelperViews.length" class="ai-section" data-test="ai-helper-section">
      <h4>AI 助手</h4>
      <div class="ai-helper-nav" data-test="ai-helper-nav">
        <button
          v-for="view in aiHelperViews"
          :key="view.id"
          :data-test="`ai-helper-tab-${view.id}`"
          type="button"
          class="ai-helper-tab"
          :class="{ 'ai-helper-tab--active': aiHelperActiveView === view.id }"
          @click="aiHelperActiveView = view.id"
        >
          {{ view.label }}
        </button>
      </div>

      <AutoQueuePanel
        v-if="aiHelperActiveView === 'auto_queue' && autoQueueStore.featureEnabled"
        :feature-enabled="autoQueueStore.featureEnabled"
        :ai-settings-blocked="aiSettingsBlocked"
        :loading="autoQueueStore.loading"
        :saving-config="autoQueueStore.savingConfig"
        :action-loading="autoQueueStore.actionLoading"
        :chapter-id="chapterId"
        :queue-mode="autoQueueMode"
        :target-chapters="autoQueueTargetChapters"
        :target-word-count="autoQueueTargetWordCount"
        :budget-limit-tokens="autoQueueBudgetLimitTokens"
        :stop-at-sequence-end="autoQueueStopAtSequenceEnd"
        :stop-on-blocking-review="autoQueueStopOnBlockingReview"
        :stop-on-budget-exceeded="autoQueueStopOnBudgetExceeded"
        :stop-on-foreshadow-premature="autoQueueStopOnForeshadowPremature"
        :current-run="autoQueueStore.currentRun"
        :history-runs="autoQueueStore.historyRuns"
        :error-message="autoQueueStore.errorMessage"
        :note-message="autoQueueStore.noteMessage"
        @update:queue-mode="autoQueueMode = $event"
        @update:target-chapters="autoQueueTargetChapters = $event"
        @update:target-word-count="autoQueueTargetWordCount = $event"
        @update:budget-limit-tokens="autoQueueBudgetLimitTokens = $event"
        @update:stop-at-sequence-end="autoQueueStopAtSequenceEnd = $event"
        @update:stop-on-blocking-review="autoQueueStopOnBlockingReview = $event"
        @update:stop-on-budget-exceeded="autoQueueStopOnBudgetExceeded = $event"
        @update:stop-on-foreshadow-premature="autoQueueStopOnForeshadowPremature = $event"
        @save-config="handleAutoQueueSaveConfig"
        @start="handleAutoQueueStart"
        @pause="handleAutoQueuePause"
        @resume="handleAutoQueueResume"
        @stop="handleAutoQueueStop"
        @confirm-continue="handleAutoQueueConfirmContinue"
        @disable-budget-check="handleAutoQueueDisableBudgetCheck"
        @view-candidates="handleAutoQueueViewCandidates"
        @view-conflicts="handleAutoQueueViewConflicts"
        @refresh="handleAutoQueueRefresh"
        @select-run="handleAutoQueueSelectRun"
      />

      <div
        v-if="aiHelperActiveView === 'auto_queue' && autoQueueConflictSectionVisible"
        data-test="auto-queue-conflicts"
      >
        <h5>自动续写冲突详情</h5>
        <p v-if="autoQueueConflictLoading" class="ai-note">正在加载冲突详情…</p>
        <p v-else-if="!autoQueueConflictItems.length" class="ai-note">当前没有可展示的阻断冲突，请刷新后重试。</p>
        <ul v-else class="ai-list">
          <li
            v-for="conflict in autoQueueConflictItems"
            :key="conflict.record_id"
            class="planning-item"
          >
            <div class="candidate-summary">
              <strong>{{ conflict.title || '待处理冲突' }}</strong>
              <span>{{ displaySeverity(conflict.severity) }}</span>
              <span>{{ conflict.summary || '请先处理冲突后再继续队列。' }}</span>
            </div>
          </li>
        </ul>
      </div>

      <OutlineAssistPanel
        v-if="aiHelperActiveView === 'outline_assist' && outlineAssistEnabled"
        :feature-enabled="outlineAssistStore.featureEnabled"
        :modes="outlineAssistStore.modes"
        :active-mode="outlineAssistStore.activeMode"
        :suggestions="outlineAssistStore.filteredSuggestions"
        :suggestion-details="outlineAssistStore.suggestionDetails"
        :action-error="outlineAssistStore.actionError"
        :submitting-suggestion-id="outlineAssistStore.submittingSuggestionId"
        :submitting-action-type="outlineAssistStore.submittingActionType"
        :loading="outlineAssistStore.loading"
        :conflict-section-visible="outlineAssistStore.conflictSectionVisible"
        :conflict-loading="outlineAssistStore.conflictLoading"
        :conflict-items="outlineAssistStore.conflictItems"
        :conflict-details="outlineAssistStore.conflictDetails"
        :apply-confirm-suggestion-id="outlineAssistStore.applyConfirmSuggestionId"
        :apply-submitting-suggestion-id="outlineAssistStore.applySubmittingSuggestionId"
        :can-accept-suggestion="outlineAssistStore.canAcceptSuggestion"
        :can-resolve-suggestion="outlineAssistStore.canResolveSuggestion"
        :can-convert-suggestion="outlineAssistStore.canConvertSuggestion"
        :can-apply-suggestion="outlineAssistStore.canApplySuggestion"
        :is-accepted-writing-task-suggestion="outlineAssistStore.isAcceptedWritingTaskSuggestion"
        :is-selection-only-suggestion="outlineAssistStore.isSelectionOnlySuggestion"
        :is-stale-suggestion="outlineAssistStore.isStaleSuggestion"
        :display-suggestion-type="displaySuggestionType"
        :display-severity="displaySeverity"
        @update:active-mode="outlineAssistStore.setActiveMode"
        @suggestion-detail="outlineAssistStore.loadSuggestionDetail"
        @suggestion-accept="outlineAssistStore.acceptSuggestion"
        @suggestion-apply-open="outlineAssistStore.openApplyConfirm"
        @suggestion-dismiss="outlineAssistStore.dismissSuggestion"
        @suggestion-convert="outlineAssistStore.convertSuggestionWithConflictSync"
        @suggestion-apply-cancel="outlineAssistStore.closeApplyConfirm"
        @suggestion-apply-confirm-submit="handleApplyOutlineSuggestion"
        @refresh="loadAISuggestions"
      />

      <div
        v-if="aiHelperActiveView === 'opening_agent' && openingAgentEnabled"
        class="ai-helper-view"
        data-test="opening-agent-view"
      >
        <h5>开篇助手</h5>
        <p class="ai-note">导入参考、分析开篇特点、确认策略与风险后，再进入正式候选稿生成链路。</p>
        <p class="ai-note" data-test="opening-agent-preview-status">
          {{ openingPreviewStatusHint }}
        </p>
        <p class="ai-note" data-test="opening-agent-last-result">
          {{ openingLastSnapshotResultHint }}
        </p>
        <p class="ai-note" data-test="opening-agent-last-updated">
          {{ openingLastSnapshotUpdatedHint }}
        </p>
        <div class="opening-preview-grid">
          <div class="opening-preview-card" data-test="opening-agent-summary">
            <strong>分析摘要</strong>
            <span>{{ openingStore.analysis.analysis_summary }}</span>
          </div>
          <div class="opening-preview-card" data-test="opening-agent-strategy">
            <strong>目标读者</strong>
            <span>{{ openingStore.strategy.target_audience }}</span>
            <strong>开篇钩子</strong>
            <span>{{ openingStore.strategy.opening_hook }}</span>
          </div>
          <div class="opening-preview-card" data-test="opening-agent-strategy-details">
            <strong>类型定位</strong>
            <span>{{ openingStore.strategy.genre_positioning }}</span>
            <strong>前三章目标</strong>
            <span>{{ openingStore.strategy.first_three_chapter_goal }}</span>
            <strong>避相似提醒</strong>
            <span>{{ openingStore.strategy.forbidden_similarity_notes }}</span>
          </div>
          <div class="opening-preview-card" data-test="opening-agent-strategy-structure">
            <strong>主角登场</strong>
            <span>{{ openingStore.strategy.protagonist_entry }}</span>
            <strong>冲突引入</strong>
            <span>{{ openingStore.strategy.conflict_entry }}</span>
            <strong>签约卖点</strong>
            <span>{{ (openingStore.strategy.selling_points || []).join(' / ') }}</span>
          </div>
          <div class="opening-preview-card" data-test="opening-agent-runtime">
            <strong>当前阶段</strong>
            <span>{{ openingStore.phase || '-' }}</span>
            <strong>执行状态</strong>
            <span>{{ displayStatus(openingStore.status || 'unknown') }}</span>
            <strong>已生成候选稿</strong>
            <span>{{ openingStore.candidateDraftIds.length }}</span>
          </div>
        </div>
        <div
          :class="[
            'conflict-banner',
            openingPreviewRiskBlocking ? 'conflict-banner-blocking' : 'conflict-banner-warning'
          ]"
          data-test="opening-agent-risk"
        >
          <strong>{{ openingPreviewRiskLabel }}</strong>
          <span>{{ openingPreviewRiskHint }}</span>
        </div>
        <div class="ai-actions">
          <button
            data-test="opening-agent-refresh"
            type="button"
            :disabled="!workId || openingRefreshSubmitting || openingInitialLoading"
            @click="handleOpeningRefresh"
          >
            {{ openingRefreshSubmitting ? '刷新中...' : '刷新快照' }}
          </button>
          <button
            data-test="opening-agent-open"
            type="button"
            :disabled="aiSettingsBlocked"
            @click="openingWizardVisible = true"
          >
            打开开篇助手
          </button>
        </div>
      </div>
    </div>

    <OpeningAgentWizard
      :visible="openingWizardVisible"
      :analysis="openingStore.analysis"
      :strategy="openingStore.strategy"
      :risk-level="openingStore.riskLevel"
      @close="openingWizardVisible = false"
      @generate="handleOpeningGenerate"
    />

    <div v-if="showAIMode" class="ai-section">
      <h4>向量索引</h4>
      <div v-if="vectorIndexNeedsAttention" class="settings-block-banner" data-test="vector-index-stale-banner">
        <strong>索引已过期，点击重建</strong>
        <span>{{ vectorIndexBannerMessage }}</span>
      </div>
      <div class="ai-actions">
        <button
          data-test="vector-index-reindex-full-work"
          type="button"
          :disabled="aiSettingsBlocked || reindexSubmitting"
          @click="handleStartVectorReindex('full_work')"
        >
          重建整部作品索引
        </button>
        <button
          data-test="vector-index-reindex-current-chapter"
          type="button"
          :disabled="aiSettingsBlocked || reindexSubmitting || !chapterId"
          @click="handleStartVectorReindex('chapter')"
        >
          重建当前章节索引
        </button>
        <button
          v-if="vectorIndexJobActive"
          data-test="vector-index-cancel"
          type="button"
          @click="handleCancelVectorReindex"
        >
          取消重建
        </button>
        <button
          v-if="vectorIndexRetryVisible"
          data-test="vector-index-retry"
          type="button"
          :disabled="reindexSubmitting"
          @click="handleRetryVectorReindex"
        >
          重试
        </button>
      </div>
      <div class="ai-meta">
        <span>状态 {{ displayStatus(vectorIndexDisplayStatus) }}</span>
        <span v-if="reindexPolling.jobId.value">任务 {{ reindexPolling.jobId.value }}</span>
        <span v-if="vectorIndexStatusHint">{{ vectorIndexStatusHint }}</span>
        <span v-if="vectorIndexProgressPercent > 0">进度 {{ vectorIndexProgressPercent }}%</span>
        <span v-if="vectorIndexStepLabel">{{ vectorIndexStepLabel }}</span>
      </div>
      <p v-if="reindexActionError" class="ai-error">{{ reindexActionError }}</p>
    </div>

    <div v-if="showAIMode && plotArcVisible" class="ai-section">
      <h4>剧情轨道详情</h4>
      <div class="ai-meta">
        <span>{{ displayStatus(contextPackReadiness.status || 'unknown') }}</span>
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
          {{ displayArcLevel(key) }}: {{ displayStatus(value.status || 'unknown') }}
        </span>
      </div>
      <ul v-if="plotArcs.length" class="ai-list">
        <li v-for="arc in plotArcs" :key="arc.arc_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ arc.title || arc.arc_id }}</strong>
            <span>{{ displayArcLevel(arc.arc_level) }}</span>
            <span>{{ displayStatus(arc.status) }}</span>
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
      <h4>AI 写作任务</h4>
      <ul v-if="agentSessions.length" class="ai-list">
        <li v-for="session in agentSessions" :key="session.session_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ session.session_id }}</strong>
            <span>{{ displayStatus(session.status) }}</span>
            <span>{{ displayWorkflowType(session.workflow_type) }}</span>
            <span>{{ displayAgentType(session.current_agent_type || session.current_stage || '-') }}</span>
              <span v-if="session.progress_percent !== undefined">进度 {{ session.progress_percent }}%</span>
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
            <span>{{ displayStatus(agentSessionDetails[session.session_id].status) }}</span>
            <span>{{ displayWorkflowStage(agentSessionDetails[session.session_id].current_stage || '-') }}</span>
            <span>{{ displayAgentType(agentSessionDetails[session.session_id].current_agent_type || '-') }}</span>
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
            <span>{{ displayStatus(proposal.status) }}</span>
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
            <span>{{ displayStatus(plan.status) }}</span>
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
        <li v-for="task in writingTasks" :key="task.writing_task_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ task.writing_task_id }}</strong>
            <span>{{ displayStatus(task.status) }}</span>
            <span>{{ task.writing_goal }}</span>
            <span>{{ task.plan_summary }}</span>
            <span>{{ displayWritingTaskConfirmation(task) }}</span>
          </div>
          <div class="ai-actions">
            <button
              :data-test="`writing-task-detail-${task.writing_task_id}`"
              type="button"
              @click="handleWritingTaskDetail(task.writing_task_id)"
            >
              查看任务详情
            </button>
            <button
              :data-test="`writing-task-confirm-${task.writing_task_id}`"
              type="button"
              :disabled="task.status !== 'ready' || isWritingTaskConfirmed(task) || writingTaskSubmittingId === task.writing_task_id"
              @click="handleConfirmWritingTask(task.writing_task_id)"
            >
              {{ writingTaskSubmittingId === task.writing_task_id ? '确认中...' : isWritingTaskConfirmed(task) ? '已确认可执行' : '确认可执行' }}
            </button>
          </div>
          <div v-if="writingTaskDetails[task.writing_task_id]" class="note-box">
            <div>目标：{{ writingTaskDetails[task.writing_task_id].writing_goal || '未填写' }}</div>
            <div>必须包含：{{ (writingTaskDetails[task.writing_task_id].must_include || []).join('；') || '无' }}</div>
            <div>禁止事项：{{ (writingTaskDetails[task.writing_task_id].must_not_include || []).join('；') || '无' }}</div>
            <div>计划摘要：{{ writingTaskDetails[task.writing_task_id].plan_summary || '无' }}</div>
          </div>
        </li>
      </ul>
      <p v-if="planningActionError" class="ai-error">{{ planningActionError }}</p>
    </div>

    <div v-if="false" class="ai-section">
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
        <strong>{{ conflictSummary.blockingCount ? '资产冲突待处理' : '资产风险需确认' }}</strong>
          <span v-if="conflictSummary.blockingCount">存在阻断项 {{ conflictSummary.blockingCount }}，应用前必须处理。</span>
          <span v-else>存在警告 {{ conflictSummary.warningCount }}，继续应用代表你已知晓风险。</span>
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
            <span>{{ displayValidationStatus(item.validation_status) }}</span>
            <span>{{ item.source_context_pack_id }}</span>
              <span v-if="conflictCountsByDraft[item.candidate_draft_id]?.warning">警告 {{ conflictCountsByDraft[item.candidate_draft_id].warning }}</span>
            <span v-if="conflictCountsByDraft[item.candidate_draft_id]?.blocking">阻断 blocking {{ conflictCountsByDraft[item.candidate_draft_id].blocking }}</span>
            <span v-if="conflictCountsByDraft[item.candidate_draft_id]?.info">提示 info {{ conflictCountsByDraft[item.candidate_draft_id].info }}</span>
            <span v-if="item.selected_version_id">已选择版本 {{ item.selected_version_id }}</span>
            <span v-if="item.accepted_version_id">已接受版本 {{ item.accepted_version_id }}</span>
            <span v-if="item.applied_version_id">已应用版本 {{ item.applied_version_id }}</span>
          </div>
          <div class="ai-actions">
            <button :data-test="`candidate-detail-${item.candidate_draft_id}`" type="button" @click="loadCandidateDetail(item.candidate_draft_id)">
              查看详情
            </button>
              <button :data-test="`candidate-accept-${item.candidate_draft_id}`" type="button" @click="handleAcceptCandidate(item.candidate_draft_id)">
              接受候选稿
            </button>
              <button :data-test="`candidate-reject-${item.candidate_draft_id}`" type="button" @click="handleRejectCandidate(item.candidate_draft_id)">
              拒绝候选稿
            </button>
              <button :data-test="`candidate-apply-${item.candidate_draft_id}`" type="button" @click="handleApplyCandidate(item.candidate_draft_id)">
              应用到章节草稿
            </button>
            <button
              :data-test="`candidate-review-${item.candidate_draft_id}`"
              type="button"
              :disabled="aiSettingsBlocked"
              @click="handleReviewCandidate(item.candidate_draft_id)"
            >
              AI 审阅
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
                <span>{{ displayStatus(version.status) }}</span>
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
                  查看版本差异
                </button>
                <button
                  :data-test="`candidate-version-rewrite-review-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'review_based')"
                >
                  按审阅意见修订                </button>
                <button
                  :data-test="`candidate-version-rewrite-user-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleRewriteCandidate(item.candidate_draft_id, version.candidate_version_id, 'user_instruction')"
                >
                  输入要求后重写                </button>
                <button
                  :data-test="`candidate-version-reject-${item.candidate_draft_id}-${version.candidate_version_id}`"
                  type="button"
                  @click="handleRejectCandidateVersion(item.candidate_draft_id, version.candidate_version_id)"
                >
                  拒绝此版本                </button>
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
                <span>{{ displayConflictType(conflict.conflict_type) }}</span>
                <span>{{ displaySeverity(conflict.severity) }}</span>
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
                  稍后处理
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

    <div v-if="false" class="ai-section">
      <h4>记忆审批</h4>
      <ul v-if="memoryGates.length" class="ai-list">
        <li v-for="gate in memoryGates" :key="gate.gate_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ gate.gate_id }}</strong>
            <span>{{ displayStatus(gate.state) }}</span>
            <span>建议数 {{ (gate.suggestions || []).length }}</span>
          </div>
          <ul class="ai-list">
            <li v-for="suggestion in gate.suggestions || []" :key="suggestion.id" class="planning-item">
              <div class="candidate-summary">
                <strong>{{ displayMemoryTargetType(suggestion.target_memory_type) }}</strong>
                <span>{{ displayRevisionType(suggestion.revision_type) }}</span>
                <span>{{ displayStatus(suggestion.status) }}</span>
                <span>{{ suggestion.current_value_summary }}</span>
                <span>{{ suggestion.proposed_value_summary }}</span>
              </div>
              <div class="ai-actions">
                <button
                  :data-test="`memory-approve-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleApproveMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  审批通过
                </button>
                <button
                  :data-test="`memory-edit-approve-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleEditApproveMemorySuggestion(gate.gate_id, suggestion)"
                >
                  编辑后通过
                </button>
                <button
                  :data-test="`memory-reject-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleRejectMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  拒绝建议
                </button>
                <button
                  :data-test="`memory-defer-${gate.gate_id}-${suggestion.id}`"
                  type="button"
                  @click="handleDeferMemorySuggestion(gate.gate_id, suggestion.id)"
                >
                  稍后处理
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
              应用本组修订
            </button>
          </div>
          <ul v-if="gate.revision_ids?.length" class="ai-list">
            <li v-for="revisionId in gate.revision_ids" :key="revisionId">
              <div class="candidate-summary">
                <strong>{{ revisionId }}</strong>
                <span>{{ displayStatus(memoryRevisionDetails[revisionId]?.status || 'revision') }}</span>
              </div>
              <div class="ai-actions">
                <button
                  :data-test="`memory-revision-detail-${revisionId}`"
                  type="button"
                  @click="handleMemoryRevisionDetail(revisionId)"
                >
                  查看修订详情
                </button>
                <button
                  v-if="memoryRevisionDetails[revisionId]?.status === 'applied'"
                  :data-test="`memory-revision-rollback-${revisionId}`"
                  type="button"
                  @click="handleRollbackMemoryRevision(revisionId)"
                >
                   执行回滚
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

    <div v-if="false" class="ai-section">
      <h4>任务追踪</h4>
      <ul v-if="agentTraces.length" class="ai-list">
        <li v-for="trace in agentTraces" :key="trace.trace_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ trace.trace_id }}</strong>
            <span>{{ displayStatus(trace.status) }}</span>
            <span>{{ displayWorkflowType(trace.workflow_type) }}</span>
            <span>步骤数 {{ trace.total_steps || 0 }}</span>
            <span>Token {{ trace.total_tokens || 0 }}</span>
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
              查看详细（Detail）
            </button>
          </div>
          <ul v-if="agentTraceSteps[trace.trace_id]?.length" class="ai-list">
            <li v-for="step in agentTraceSteps[trace.trace_id]" :key="step.step_id">
              {{ displayAgentType(step.agent_type) }} / {{ displayStepAction(step.action) }} / {{ displayStatus(step.status) }}
            </li>
          </ul>
          <div v-if="agentTraceDetails[trace.trace_id]" class="ai-note">
            <div v-if="agentTraceDetails[trace.trace_id].tool_calls?.length">
              工具调用 {{ displayToolName(agentTraceDetails[trace.trace_id].tool_calls[0].tool_name) }} / {{ displayPermissionResult(agentTraceDetails[trace.trace_id].tool_calls[0].permission_result) }}
            </div>
            <div v-if="agentTraceDetails[trace.trace_id].events?.length">
              事件 {{ displayEventType(agentTraceDetails[trace.trace_id].events[0].event_type) }}
            </div>
            <ul v-if="agentTraceDetails[trace.trace_id].metrics?.length" class="ai-list">
              <li v-for="metric in agentTraceDetails[trace.trace_id].metrics" :key="metric.metric_id">
                {{ displayMetricName(metric.metric_name) }} / {{ metric.metric_value }}
              </li>
            </ul>
            <ul v-if="agentTraceDetails[trace.trace_id].alerts?.length" class="ai-list">
              <li v-for="alert in agentTraceDetails[trace.trace_id].alerts" :key="alert.alert_id">
                {{ displayAlertType(alert.alert_type) }} / {{ displayStatus(alert.status) }} / {{ alert.summary }}
              </li>
            </ul>
            <ul v-if="agentTraceDetails[trace.trace_id].user_decisions?.length" class="ai-list">
              <li v-for="decision in agentTraceDetails[trace.trace_id].user_decisions" :key="decision.decision_trace_id">
                {{ displayDecisionType(decision.decision_type) }} / {{ displayEntityType(decision.target_entity_type) }} / {{ decision.target_entity_id }}
              </li>
            </ul>
          </div>
        </li>
      </ul>
      <p v-if="traceActionError" class="ai-error">{{ traceActionError }}</p>
    </div>

    <div v-if="showAIMode" class="ai-section">
      <h4>快速试写</h4>
      <div class="field-grid">
        <input v-model="quickTrialForm.input_text" type="text" placeholder="输入试写内容或指令摘要" />
        <input v-model="quickTrialForm.model_role" type="text" placeholder="试写角色" />
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
        <span v-if="quickTrialResult.status">{{ displayStatus(quickTrialResult.status) }}</span>
        <span v-if="quickTrialResult.validation_status">{{ displayValidationStatus(quickTrialResult.validation_status) }}</span>
      </div>
      <pre v-if="quickTrialResult.output_text" class="quick-trial-output">{{ quickTrialResult.output_text }}</pre>
    </div>
    </template>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'
import { useAIJobPolling } from '@/composables/useAIJobPolling'
import { useAutoQueueStore } from '@/stores/useAutoQueueStore'
import { useOutlineAssistStore } from '@/stores/useOutlineAssistStore'
import { useOpeningStore } from '@/stores/useOpeningStore'
import { useStyleDNAStore } from '@/stores/useStyleDNAStore'
import AutoQueuePanel from './AutoQueuePanel.vue'
import OpeningAgentWizard from './OpeningAgentWizard.vue'
import OutlineAssistPanel from './OutlineAssistPanel.vue'
import ReviewTab from './ReviewTab.vue'
import StyleDNAConfigPanel from './StyleDNAConfigPanel.vue'

const emit = defineEmits(['open-review-tab'])

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
  chapterOptions: {
    type: Array,
    default: () => []
  },
  draftChapterIds: {
    type: Array,
    default: () => []
  },
  mode: {
    type: String,
    default: 'all'
  }
})

const router = useRouter()
let reindexStartTimer = null
const goToSettingsPage = () => {
  router.push('/settings')
}

const REQUIRED_SETTINGS_ROLES = ['analysis', 'planning', 'writer', 'reviewer', 'rewriter']

const settings = ref({ provider_configs: [], model_role_mappings: {} })
const settingsForm = reactive({
  provider_configs: [],
  model_role_mappings: Object.fromEntries(
    REQUIRED_SETTINGS_ROLES.map((role) => [role, { provider_name: '', model_name: '' }])
  )
})
const initializationInfo = ref({})
const contextPackReadiness = ref({})
const contextPackItems = ref([])
const reindexActionError = ref('')
const reindexSubmitting = ref(false)
const lastReindexRequest = ref(null)
const continuationResult = ref({})
const candidateDrafts = ref([])
const candidateDetails = ref({})
const candidateVersions = ref({})
const candidateVersionDetails = ref({})
const candidateVersionDiffs = ref({})
const selectedVersionByDraft = ref({})
const candidateReviewByDraft = ref({})
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
const writingTaskDetails = ref({})
const writingTaskSubmittingId = ref('')
const planningActionError = ref('')
const quickTrialResult = ref({})
const styleDNADraftText = ref('')
const styleDNASourceMode = ref('user_upload')
const styleDNASelectedChapterIds = ref([])
const autoQueueMode = ref('safe')
const autoQueueTargetChapters = ref(5)
const autoQueueTargetWordCount = ref(0)
const autoQueueBudgetLimitTokens = ref(0)
const autoQueueStopAtSequenceEnd = ref(true)
const autoQueueStopOnBlockingReview = ref(true)
const autoQueueStopOnBudgetExceeded = ref(true)
const autoQueueStopOnForeshadowPremature = ref(true)
const autoQueueConflictSectionVisible = ref(false)
const autoQueueConflictLoading = ref(false)
const aiHelperActiveView = ref('auto_queue')
const outlineAssistEnabled = isP2FeatureEnabled('enable_outline_assist')
const openingAgentEnabled = isP2FeatureEnabled('enable_opening_agent')
const openingWizardVisible = ref(false)
const openingInitialLoading = ref(false)
const openingRefreshSubmitting = ref(false)
const polling = useAIJobPolling({ intervalMs: 1000 })
const reindexPolling = useAIJobPolling({ intervalMs: 3000, maxIntervalMs: 10000 })
const autoQueueStore = useAutoQueueStore()
const outlineAssistStore = useOutlineAssistStore()
const openingStore = useOpeningStore()
const styleDNAStore = useStyleDNAStore()

const styleDNAChapterOptions = computed(() => {
  const draftChapterIdSet = new Set((props.draftChapterIds || []).map((item) => String(item || '')))
  return (props.chapterOptions || []).map((chapter, index) => {
    const chapterId = String(chapter?.id || '')
    const orderIndex = Number(chapter?.order_index || index + 1)
    const status = String(chapter?.status || '')
    const title = String(chapter?.title || '').trim() || `未命名章节 ${orderIndex}`
    return {
      id: chapterId,
      label: `第${orderIndex}章 ${title}`,
      disabled: status !== 'published' || draftChapterIdSet.has(chapterId)
    }
  })
})
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

const providerConfigs = computed(() => settingsForm.provider_configs || [])
const isReviewMode = computed(() => props.mode === 'review')
const showAIMode = computed(() => props.mode !== 'review')
const showReviewMode = computed(() => props.mode !== 'ai')
const panelTitle = computed(() => (
  props.mode === 'review' ? '审阅工作区' : props.mode === 'ai' ? 'AI 工作区' : 'AI 助手'
))
const panelDescription = computed(() => (
  props.mode === 'review'
    ? '候选稿、审阅、冲突、记忆门控与任务追踪在此集中处理。'
    : props.mode === 'ai'
    ? '设置、初始化、写作上下文、剧情轨道、方向计划、会话进度与快速试写。'
    : '最小集成入口：设置、初始化、写作上下文、续写、快速试写、AI审阅。'
))
const aiHelperViews = computed(() => {
  const items = []
  if (autoQueueStore.featureEnabled) {
    items.push({ id: 'auto_queue', label: '自动续写' })
  }
  if (outlineAssistEnabled) {
    items.push({ id: 'outline_assist', label: '大纲辅助' })
  }
  if (openingAgentEnabled) {
    items.push({ id: 'opening_agent', label: '开篇助手' })
  }
  return items
})
const openingPreviewRiskLevel = computed(() => String(openingStore.riskLevel || 'warning').toLowerCase())
const openingPreviewRiskBlocking = computed(() => ['high', 'blocking'].includes(openingPreviewRiskLevel.value))
const openingPreviewRiskLabel = computed(() => ({
  low: '低风险（low）',
  medium: '中风险（medium）',
  warning: '警告（warning）',
  high: '高风险（high）',
  blocking: '阻断（blocking）'
}[openingPreviewRiskLevel.value] || '警告（warning）'))
const openingPreviewRiskHint = computed(() => (
  openingPreviewRiskBlocking.value
    ? '存在较高的模仿风险，建议返回修改策略后再生成。'
    : '风险可控，确认版权与策略后可继续进入候选稿生成。'
))
const openingPreviewStatusHint = computed(() => {
  if (openingInitialLoading.value) {
    return '正在读取 Opening API 实时快照，请稍候。'
  }
  if (openingStore.snapshotLoaded) {
    return '已读取 Opening API 实时快照，当前展示为最新只读 snapshot。'
  }
  if (openingStore.snapshotLoadFailed) {
    return '当前显示为本地预览快照；opening snapshot 读取失败，暂回退到本地预览。'
  }
  return '当前显示为本地预览快照；待后续接入 Opening API 实时结果后，再切换为联调数据。'
})
const openingLastSnapshotResultHint = computed(() => ({
  succeeded: '最近一次快照结果：读取成功。',
  failed: '最近一次快照结果：已回退到本地预览。',
  idle: '最近一次快照结果：尚未读取。'
}[openingStore.lastSnapshotOutcome] || '最近一次快照结果：尚未读取。'))
const openingLastSnapshotUpdatedHint = computed(() => (
  openingStore.lastSnapshotAt
    ? `最近更新时间：${openingStore.lastSnapshotAt}`
    : '最近更新时间：尚无。'
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
const vectorIndexWarnings = computed(() => (
  Array.isArray(contextPackReadiness.value?.warnings) ? contextPackReadiness.value.warnings.filter(Boolean) : []
))
const vectorIndexNeedsAttention = computed(() => (
  String(contextPackReadiness.value?.degraded_reason || '') === 'vector_index_stale_warning' ||
  vectorIndexWarnings.value.includes('vector_index_stale_warning') ||
  String(contextPackReadiness.value?.vector_index_status || '') === 'stale'
))
const vectorIndexBannerMessage = computed(() => (
  vectorIndexNeedsAttention.value
    ? '当前索引可能已过期，建议尽快重建。重建期间续写仍可使用现有索引。'
    : '当前索引可用于上下文召回。'
))
const vectorIndexDisplayStatus = computed(() => (
  String(reindexPolling.job.value?.status || contextPackReadiness.value?.vector_index_status || contextPackReadiness.value?.status || 'unknown')
))
const vectorIndexProgressPercent = computed(() => Number(reindexPolling.job.value?.progress?.percent || 0))
const vectorIndexStepLabel = computed(() => String(reindexPolling.job.value?.progress?.current_step_label || ''))
const vectorIndexJobActive = computed(() => Boolean(reindexPolling.jobId.value) && !reindexPolling.isTerminal.value)
const vectorIndexRetryVisible = computed(() => TERMINAL_JOB_STATUSES.has(String(reindexPolling.job.value?.status || '')) &&
  ['failed', 'cancelled'].includes(String(reindexPolling.job.value?.status || '')))
const vectorIndexStatusHint = computed(() => {
  const status = String(reindexPolling.job.value?.status || '')
  if (status === 'queued' || status === 'running') return '正在重建索引'
  if (status === 'completed') return '索引重建完成。'
  if (status === 'partial_success') {
    return '索引部分重建成功，部分章节的索引可能不完整。可以针对失败章节单独重建。'
  }
  if (status === 'failed') return '索引重建失败，可以重试。'
  if (status === 'cancelled') return '索引重建已取消。'
  return ''
})
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

const autoQueueConflictItems = computed(() => {
  const blockingItems = conflicts.value.filter((item) => String(item?.severity || '') === 'blocking')
  return blockingItems.length ? blockingItems : conflicts.value
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
    return '请先配置可用模型服务 Key，并完成分析任务模型/写作任务模型配置。'
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
    return '请先配置可用模型服务 Key，并完成分析任务模型/写作任务模型配置。'
  }
  return ''
})
const aiSettingsBlocked = computed(() => Boolean(aiSettingsBlockMessage.value))

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const isWritingTaskConfirmed = (task) => Boolean(task?.metadata?.user_confirmed)
const displayWritingTaskConfirmation = (task) => (
  isWritingTaskConfirmed(task)
    ? `已由 ${task?.metadata?.confirmed_by || '当前用户'} 确认可执行`
    : '待确认可执行'
)

const statusLabelMap = {
  pending: '待处理',
  running: '进行中',
  completed: '已完成',
  partial_success: '部分成功',
  failed: '失败',
  cancelled: '已取消',
  waiting_for_user: '等待你确认',
  paused: '已暂停',
  ready: '可继续',
  degraded: '信息可能不足',
  blocked: '无法继续',
  generated: '已生成',
  shown: '已展示',
  accepted: '已接受',
  rejected: '已拒绝',
  applied: '已应用',
  stale: '可能已过期',
  superseded: '已有新版本',
  converted: '已转化',
  revision_requested: '待修订',
  review_completed: '审阅完成',
  waiting_for_selection: '待选择方向',
  waiting_for_confirmation: '待确认计划',
  open: '已开启',
  partially_approved: '部分通过'
}

const agentTypeLabelMap = {
  memory: '理解故事',
  planner: '规划方向',
  writer: '生成候选稿',
  reviewer: '审阅稿件',
  rewriter: '修订稿件'
}

const workflowTypeLabelMap = {
  continuation: '续写流程',
  planning: '规划流程',
  review: '审阅流程',
  revision: '修订流程',
  memory: '记忆流程'
}

const workflowStageLabelMap = {
  memory_context_prepare: '理解故事',
  planning_prepare: '准备规划',
  direction_selection_waiting: '等待方向选择',
  chapter_plan_generation: '生成章节计划',
  chapter_plan_confirm_waiting: '等待计划确认',
  writing_prepare: '写作准备',
  drafting: '生成候选稿',
  reviewing: '审阅候选稿',
  rewriting: '修订候选稿',
  conflict_checking: '冲突检查',
  memory_review_waiting: '等待记忆审批'
}

const suggestionTypeLabelMap = {
  rewrite_suggestion: '改写建议',
  style_suggestion: '风格建议',
  plot_suggestion: '剧情建议',
  continuity_suggestion: '连续性建议',
  conflict_resolution_suggestion: '冲突处理建议',
  memory_update_suggestion_ref: '记忆更新建议引用',
  outline_polish: '大纲润色',
  outline_expand: '大纲扩写',
  chapter_outline_detail: '章节细纲',
  writing_task_suggestion: '写作任务建议',
  risk_warning: '风险提示'
}

const revisionTypeLabelMap = {
  character_update: '人物更新',
  setting_update: '设定更新',
  timeline_event_add: '时间线新增',
  timeline_event_update: '时间线更新',
  foreshadow_add: '伏笔新增',
  foreshadow_update: '伏笔推进',
  foreshadow_resolve: '伏笔回收',
  plot_thread_update: '剧情线索更新',
  story_state_update: '故事状态更新',
  arc_note_update: '轨道备注更新',
  continuity_note_add: '连续性备注',
  unknown_memory_update: '待确认记忆更新'
}

const severityLabelMap = {
  high: '高',
  medium: '中',
  low: '低',
  warning: '警告',
  blocking: '阻断',
  info: '提示'
}

const validationStatusLabelMap = {
  passed: '已通过',
  failed: '未通过',
  blocked: '已阻断',
  degraded: '降级通过'
}

const arcLevelLabelMap = {
  master_arc: '主线轨道',
  volume_arc: '卷轨道',
  sequence_arc: '章节序列轨道',
  immediate_window: '临近章节窗口'
}

const contextItemTypeLabelMap = {
  chapter_text: '章节正文片段',
  story_memory: '故事记忆',
  story_state: '故事状态',
  plot_arc: '剧情轨道',
  direction_plan: '方向与计划',
  continuity_note: '连续性提示'
}

const conflictTypeLabelMap = {
  character_conflict: '人物冲突',
  setting_conflict: '设定冲突',
  timeline_conflict: '时间线冲突',
  arc_conflict: '轨道冲突',
  direction_plan_conflict: '方向计划冲突',
  memory_conflict: '记忆冲突',
  foreshadow_conflict: '伏笔冲突',
  candidate_version_conflict: '候选版本冲突',
  user_draft_conflict: '用户草稿冲突',
  apply_version_conflict: '应用版本冲突',
  unknown_conflict: '待确认冲突'
}

const permissionResultLabelMap = {
  allow: '允许',
  deny: '拒绝',
  conditional: '条件允许'
}

const eventTypeLabelMap = {
  tool_call_denied: '工具调用被拒绝',
  ignored_late_result: '迟到结果已忽略',
  user_decision_recorded: '用户决策已记录',
  agent_session_started: '任务已启动',
  agent_session_completed: '任务已完成',
  agent_session_failed: '任务失败'
}

const metricNameLabelMap = {
  tool_call_latency_ms: '工具调用耗时',
  llm_token_count: '模型 Token 用量',
  step_elapsed_ms: '步骤耗时'
}

const alertTypeLabelMap = {
  audit_write_failed: '审计写入失败',
  trace_write_failed: '追踪写入失败',
  conflict_blocking_detected: '检测到阻断冲突'
}

const decisionTypeLabelMap = {
  accept_candidate: '接受候选稿',
  reject_candidate: '拒绝候选稿',
  apply_candidate: '应用候选稿',
  accept_suggestion: '采纳建议',
  dismiss_suggestion: '忽略建议',
  convert_suggestion: '转化建议',
  resolve_conflict: '处理冲突',
  override_conflict: '强制覆盖冲突',
  approve_memory: '审批记忆更新',
  reject_memory: '拒绝记忆更新',
  apply_memory: '应用记忆修订'
}

const entityTypeLabelMap = {
  candidate_draft: '候选稿',
  candidate_version: '候选版本',
  suggestion: 'AI 建议',
  conflict_record: '冲突记录',
  memory_gate: '记忆审批组',
  memory_revision: '记忆修订'
}

const memoryTargetTypeLabelMap = {
  character: '人物记忆',
  setting: '设定记忆',
  timeline: '时间线记忆',
  foreshadow: '伏笔记忆',
  plot_thread: '剧情线索记忆',
  story_state: '故事状态'
}

const stepActionLabelMap = {
  prepare: '准备（prepare）',
  execute: '执行（execute）',
  observe: '观察（observe）',
  decide: '决策（decide）',
  tool_call: '工具调用（tool_call）'
}

const readinessReasonLabelMap = {
  missing_work_id: '缺少作品标识',
  missing_chapter_id: '缺少章节标识',
  master_arc_missing: '主线轨道缺失',
  master_arc_inferred_without_outline: '主线轨道仅根据现有内容推测，可靠性不足',
  arc_placeholder_only: '剧情轨道仍是占位信息',
  volume_arc_missing: '卷轨道缺失',
  sequence_arc_missing: '章节序列轨道缺失',
  immediate_window_missing: '近期剧情窗口缺失',
  context_pack_missing: '写作上下文尚未生成',
  vector_recall_unavailable: '向量召回暂不可用',
  optional_trimmed: '部分可选信息已裁剪',
  writing_task_missing: '写作任务尚未就绪',
  direction_not_selected: '方向尚未确认',
  chapter_plan_not_confirmed: '章节计划尚未确认'
}

const displayStatus = (value) => statusLabelMap[value] || String(value || '-')
const displayAgentType = (value) => agentTypeLabelMap[value] || String(value || '-')
const displayWorkflowType = (value) => workflowTypeLabelMap[value] || String(value || '-')
const displayWorkflowStage = (value) => workflowStageLabelMap[value] || String(value || '-')
const displaySuggestionType = (value) => suggestionTypeLabelMap[value] || String(value || '-')
const displayRevisionType = (value) => revisionTypeLabelMap[value] || String(value || '-')
const displaySeverity = (value) => severityLabelMap[value] || String(value || '-')
const displayValidationStatus = (value) => validationStatusLabelMap[value] || String(value || '-')
const displayArcLevel = (value) => arcLevelLabelMap[value] || String(value || '-')
const displayContextItemType = (value) => contextItemTypeLabelMap[value] || String(value || '-')
const displayConflictType = (value) => conflictTypeLabelMap[value] || String(value || '-')
const displayPermissionResult = (value) => permissionResultLabelMap[value] || String(value || '-')
const displayEventType = (value) => eventTypeLabelMap[value] || String(value || '-')
const displayMetricName = (value) => metricNameLabelMap[value] || String(value || '-')
const displayAlertType = (value) => alertTypeLabelMap[value] || String(value || '-')
const displayDecisionType = (value) => decisionTypeLabelMap[value] || String(value || '-')
const displayEntityType = (value) => entityTypeLabelMap[value] || String(value || '-')
const displayToolName = (value) => String(value || '-')
const displayStepAction = (value) => stepActionLabelMap[value] || String(value || '-')
const displayMemoryTargetType = (value) => memoryTargetTypeLabelMap[value] || String(value || '-')
const displayReadinessReason = (value) => readinessReasonLabelMap[value] || String(value || '-')
const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const REINDEX_SESSION_KEY_PREFIX = 'inktrace.vector-reindex.pending'
const TERMINAL_JOB_STATUSES = new Set(['completed', 'failed', 'cancelled', 'partial_success'])

const buildReindexStorageKey = () => `${REINDEX_SESSION_KEY_PREFIX}:${props.workId || 'unknown'}`
const savePendingReindexRequest = (payload) => {
  if (typeof window === 'undefined' || !window.sessionStorage || !props.workId) return
  window.sessionStorage.setItem(buildReindexStorageKey(), JSON.stringify({ request: payload }))
}
const loadPendingReindexRequest = () => {
  if (typeof window === 'undefined' || !window.sessionStorage || !props.workId) return null
  try {
    return JSON.parse(window.sessionStorage.getItem(buildReindexStorageKey()) || 'null')
  } catch {
    return null
  }
}

const handleStartVectorReindex = async (indexScope) => {
  const payload = buildVectorReindexRequest(indexScope)
  lastReindexRequest.value = payload
  await startVectorReindexFlow(payload)
}

const handleCancelVectorReindex = async () => {
  if (!reindexPolling.jobId.value) return
  try {
    const payload = unwrapData(await aiApi.cancelAIJob(reindexPolling.jobId.value, { reason: 'user_cancelled' }))
    clearReindexStartTimer()
    syncReindexJobState(payload)
    reindexPolling.stop()
    clearPendingReindexRequest()
    reindexActionError.value = '索引重建已取消。'
  } catch (error) {
    reindexActionError.value = String(error?.userMessage || error?.message || '索引取消失败，请稍后重试')
  }
}

const handleRetryVectorReindex = async () => {
  const baseRequest = lastReindexRequest.value || loadPendingReindexRequest()?.request
  if (!baseRequest) {
    reindexActionError.value = '缺少可重试的索引请求，请重新发起重建。'
    return
  }
  const retryPayload = buildVectorReindexRequest(baseRequest.index_scope, {
    ...baseRequest,
    idempotency_key: buildIdempotencyKey(`vector_reindex_retry_${baseRequest.index_scope}`)
  })
  lastReindexRequest.value = retryPayload
  await startVectorReindexFlow(retryPayload, { skipConfirm: true })
}
const clearPendingReindexRequest = () => {
  if (typeof window === 'undefined' || !window.sessionStorage || !props.workId) return
  window.sessionStorage.removeItem(buildReindexStorageKey())
}

const handleStyleDNAExtract = async () => {
  if (styleDNASourceMode.value === 'chapter_reference') {
    if (!styleDNASelectedChapterIds.value.length) {
      styleDNAStore.errorMessage = '请先选择 1-3 个已确认章节。'
      return
    }
    await styleDNAStore.startExtract({
      sourceType: 'chapter_reference',
      sourceChapterIds: styleDNASelectedChapterIds.value,
      availableChapters: props.chapterOptions,
      draftChapterIds: props.draftChapterIds
    })
    return
  }
  if (!styleDNADraftText.value.trim()) {
    styleDNAStore.errorMessage = '请先粘贴标杆文本。'
    return
  }
  await styleDNAStore.startExtract({
    sourceText: styleDNADraftText.value,
    sourceType: 'user_upload',
    sourceRef: props.chapterId ? `chapter:${props.chapterId}` : 'manual'
  })
}

const handleStyleDNAConfirm = async (profileId) => {
  await styleDNAStore.confirmProfile(profileId)
}

const handleStyleDNADisable = async (profileId) => {
  await styleDNAStore.disableProfile(profileId)
}

const handleStyleDNADelete = async (profileId) => {
  await styleDNAStore.deleteProfile(profileId)
}

const handleStyleDNAViewProfile = async (profileId) => {
  await styleDNAStore.loadProfile(profileId)
}

const handleStyleDNARefresh = async () => {
  await styleDNAStore.refreshProfiles(props.workId)
}

const syncAutoQueueDraftsFromStore = () => {
  autoQueueMode.value = String(autoQueueStore.config?.queue_mode || 'safe')
  autoQueueTargetChapters.value = Number(autoQueueStore.config?.target_chapters || 5)
  autoQueueTargetWordCount.value = Number(autoQueueStore.config?.target_word_count || 0)
  autoQueueBudgetLimitTokens.value = Number(autoQueueStore.config?.budget_limit_tokens || 0)
  autoQueueStopAtSequenceEnd.value = Boolean(autoQueueStore.config?.stop_at_sequence_end ?? true)
  autoQueueStopOnBlockingReview.value = Boolean(autoQueueStore.config?.stop_on_blocking_review ?? true)
  autoQueueStopOnBudgetExceeded.value = Boolean(autoQueueStore.config?.stop_on_budget_exceeded ?? true)
  autoQueueStopOnForeshadowPremature.value = Boolean(autoQueueStore.config?.stop_on_foreshadow_premature ?? true)
}

const handleAutoQueueSaveConfig = async () => {
  await autoQueueStore.saveConfig({
    queue_mode: autoQueueMode.value,
    target_chapters: Number(autoQueueTargetChapters.value || 0),
    target_word_count: Number(autoQueueTargetWordCount.value || 0),
    budget_limit_tokens: Number(autoQueueBudgetLimitTokens.value || 0),
    stop_at_sequence_end: Boolean(autoQueueStopAtSequenceEnd.value),
    stop_on_blocking_review: Boolean(autoQueueStopOnBlockingReview.value),
    stop_on_budget_exceeded: Boolean(autoQueueStopOnBudgetExceeded.value),
    stop_on_foreshadow_premature: Boolean(autoQueueStopOnForeshadowPremature.value)
  })
  syncAutoQueueDraftsFromStore()
}

const handleAutoQueueStart = async () => {
  if (!ensureAISettingsReady(planningActionError)) return
  if (!props.chapterId) {
    autoQueueStore.errorMessage = '请先进入目标章节，再启动自动续写。'
    return
  }
  await handleAutoQueueSaveConfig()
  await autoQueueStore.startQueue({ startChapterId: props.chapterId })
}

const handleAutoQueuePause = async () => {
  const runId = String(autoQueueStore.currentRun?.run_id || '')
  if (!runId) return
  await autoQueueStore.pauseQueue(runId)
}

const handleAutoQueueResume = async () => {
  const runId = String(autoQueueStore.currentRun?.run_id || '')
  if (!runId) return
  await autoQueueStore.resumeQueue(runId)
}

const handleAutoQueueConfirmContinue = async () => {
  const runId = String(autoQueueStore.currentRun?.run_id || '')
  if (!runId) return
  await autoQueueStore.confirmContinue(runId)
}

const handleAutoQueueDisableBudgetCheck = async () => {
  const confirmed = typeof window === 'undefined' || typeof window.confirm !== 'function'
    ? true
    : window.confirm('关闭预算检查后，AI 功能将不再受预算限制。确定要关闭吗？')
  if (!confirmed) return
  await autoQueueStore.saveConfig({
    queue_mode: autoQueueMode.value,
    target_chapters: Number(autoQueueTargetChapters.value || 0),
    target_word_count: Number(autoQueueTargetWordCount.value || 0),
    budget_limit_tokens: Number(autoQueueBudgetLimitTokens.value || 0),
    stop_at_sequence_end: Boolean(autoQueueStopAtSequenceEnd.value),
    stop_on_blocking_review: Boolean(autoQueueStopOnBlockingReview.value),
    stop_on_budget_exceeded: false,
    stop_on_foreshadow_premature: Boolean(autoQueueStopOnForeshadowPremature.value)
  })
  syncAutoQueueDraftsFromStore()
}

const handleAutoQueueViewConflicts = async () => {
  autoQueueConflictSectionVisible.value = true
  autoQueueConflictLoading.value = true
  try {
    await loadConflicts()
  } finally {
    autoQueueConflictLoading.value = false
  }
}

const handleOpeningGenerate = () => {
  openingWizardVisible.value = false
  ElMessage.info('开篇助手入口已接入，正式生成链路待后续联调。')
}

const handleOpeningRefresh = async () => {
  if (!props.workId || openingRefreshSubmitting.value) return
  openingRefreshSubmitting.value = true
  try {
    await openingStore.loadOpeningSnapshot(props.workId)
  } finally {
    openingRefreshSubmitting.value = false
  }
}

const handleAutoQueueStop = async () => {
  const runId = String(autoQueueStore.currentRun?.run_id || '')
  if (!runId) return
  const confirmed = typeof window === 'undefined' || typeof window.confirm !== 'function'
    ? true
    : window.confirm('确定要停止自动续写吗？已生成的候选稿会保留。')
  if (!confirmed) return
  await autoQueueStore.stopQueue(runId)
}

const handleAutoQueueRefresh = async () => {
  await autoQueueStore.refreshAll(props.workId)
  syncAutoQueueDraftsFromStore()
}

const handleAutoQueueViewCandidates = () => {
  emit('open-review-tab')
}

const handleAutoQueueSelectRun = async (runId) => {
  await autoQueueStore.selectRun(runId)
}

const buildVectorReindexRequest = (indexScope, overrides = {}) => {
  const payload = {
    work_id: props.workId,
    index_scope: indexScope,
    caller_type: 'user_action',
    force_rebuild: false,
    reason: indexScope === 'chapter'
      ? '用户在 AI 面板中手动触发当前章节索引重建'
      : '用户在 AI 面板中手动触发整部作品索引重建',
    idempotency_key: overrides.idempotency_key || buildIdempotencyKey(`vector_reindex_${indexScope}`)
  }
  if (indexScope === 'chapter') {
    payload.target_chapter_ids = [props.chapterId].filter(Boolean)
  }
  return {
    ...payload,
    ...overrides
  }
}

const buildReindexConfirmMessage = (payload) => {
  if (payload.index_scope === 'chapter') {
    const targetCount = Array.isArray(payload.target_chapter_ids) ? payload.target_chapter_ids.filter(Boolean).length : 0
    return `将对已选的 ${targetCount} 个章节重建向量索引。确认开始？`
  }
  return '将重建全部已确认章节的向量索引。重建期间续写仍可使用现有索引。确认开始？'
}

const syncReindexJobState = (payload) => {
  reindexPolling.job.value = {
    ...(reindexPolling.job.value || {}),
    ...payload
  }
}

const clearReindexStartTimer = () => {
  if (!reindexStartTimer) return
  clearTimeout(reindexStartTimer)
  reindexStartTimer = null
}

const seedReindexPolling = (payload, options = {}) => {
  const { autoPoll = true } = options
  clearReindexStartTimer()
  reindexPolling.stop()
  reindexPolling.jobId.value = String(payload.job_id || '')
  reindexPolling.pollingHint.value = payload.polling_hint && typeof payload.polling_hint === 'object'
    ? payload.polling_hint
    : {}
  syncReindexJobState(payload)
  if (!autoPoll || !reindexPolling.jobId.value || TERMINAL_JOB_STATUSES.has(String(payload.status || ''))) {
    return
  }
  const delayMs = Number(reindexPolling.pollingHint.value?.next_poll_after_ms || 3000)
  reindexStartTimer = setTimeout(() => {
    reindexStartTimer = null
    void reindexPolling.fetchOnce()
  }, Number.isFinite(delayMs) && delayMs > 0 ? delayMs : 3000)
}

const startVectorReindexFlow = async (payload, options = {}) => {
  const {
    skipConfirm = false,
    autoPoll = true,
    successMessage = '索引重建已加入队列，即将开始。'
  } = options
  reindexActionError.value = ''
  if (!ensureAISettingsReady(reindexActionError)) return
  if (!props.workId) return
  if (payload.index_scope === 'chapter' && !(payload.target_chapter_ids || []).length) {
    reindexActionError.value = '请选择至少一个章节。'
    return
  }
  if (!skipConfirm) {
    const confirmed = typeof window === 'undefined' || typeof window.confirm !== 'function'
      ? true
      : window.confirm(buildReindexConfirmMessage(payload))
    if (!confirmed) return
  }
  reindexSubmitting.value = true
  try {
    const response = unwrapData(await aiApi.startVectorIndexReindex(payload))
    lastReindexRequest.value = payload
    savePendingReindexRequest(payload)
    if (response.job_id) {
      seedReindexPolling(response, { autoPoll })
    } else {
      syncReindexJobState(response)
    }
    if (response.reused_existing_job) {
      ElMessage.success('已恢复索引重建任务。')
    } else {
      ElMessage.success(successMessage)
    }
  } catch (error) {
    reindexActionError.value = String(error?.userMessage || error?.message || '索引重建失败，可以重试。')
  } finally {
    reindexSubmitting.value = false
  }
}

const restorePendingVectorReindex = async () => {
  if (!showAIMode.value || !props.workId || reindexSubmitting.value || reindexPolling.jobId.value) return
  const pending = loadPendingReindexRequest()
  const request = pending?.request
  if (!request || String(request.work_id || '') !== String(props.workId || '')) return
  await startVectorReindexFlow(request, {
    skipConfirm: true,
    autoPoll: false,
    successMessage: '已恢复索引重建任务。'
  })
}

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
  try {
    await outlineAssistStore.loadSuggestions({
      workId: props.workId,
      chapterId: props.chapterId
    })
  } catch (error) {
    outlineAssistStore.setActionError(String(error?.userMessage || '大纲建议加载失败，请稍后重试'))
  }
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

const refreshAIPanel = async () => {
  await Promise.all([
    loadSettings(),
    loadInitialization(),
    loadContextReadiness(),
    loadAgentSessions(),
    loadPlotArcs(),
    loadPlanningData()
  ])
}

const refreshReviewPanel = async () => {
  await Promise.all([
    loadCandidateDrafts(),
    loadAISuggestions(),
    loadMemoryGates(),
    loadConflicts(),
    loadAgentTraces()
  ])
}

const refreshPanel = async () => {
  if (isReviewMode.value) {
    return refreshReviewPanel()
  }
  return refreshAIPanel()
}

const ensureAISettingsReady = (targetRef) => {
  if (!aiSettingsBlocked.value) return true
  const message = aiSettingsBlockMessage.value
  if (targetRef) {
    targetRef.value = message
  }
  return false
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
    planningActionError.value = String(error?.userMessage || error?.message || '方向推演生成失败，请稍后重试')
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
    planningActionError.value = String(error?.userMessage || error?.message || '方向选择失败，请稍后重试')
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
    planningActionError.value = String(error?.userMessage || error?.message || '章节计划生成失败，请稍后重试')
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
    planningActionError.value = String(error?.userMessage || error?.message || '章节计划确认失败，请稍后重试')
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
    planningActionError.value = String(error?.userMessage || error?.message || '章节计划拒绝失败，请稍后重试')
  }
}

const handleWritingTaskDetail = async (writingTaskId) => {
  planningActionError.value = ''
  try {
    const payload = unwrapData(await aiApi.getWritingTask(writingTaskId))
    writingTaskDetails.value = {
      ...writingTaskDetails.value,
      [writingTaskId]: payload
    }
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || '写作任务详情加载失败，请稍后重试')
  }
}

const handleConfirmWritingTask = async (writingTaskId) => {
  planningActionError.value = ''
  writingTaskSubmittingId.value = writingTaskId
  try {
    await aiApi.confirmWritingTask(writingTaskId, {
      caller_type: 'user_action',
      user_action: true,
      user_id: 'ui-user',
      decision_note: 'manual confirm writing task ready',
      idempotency_key: buildIdempotencyKey('writing_task_confirm')
    })
    await loadPlanningData()
    await handleWritingTaskDetail(writingTaskId)
  } catch (error) {
    planningActionError.value = String(error?.userMessage || error?.message || '写作任务确认失败，请稍后重试')
  } finally {
    writingTaskSubmittingId.value = ''
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
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿接受失败，请稍后重试')
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
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿拒绝失败，请稍后重试')
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
        `存在 ${warningItems.length} 条警告。继续应用代表你已知晓风险，是否继续？`
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
    ElMessage.success('应用成功')
    await loadCandidateDrafts()
    await loadCandidateDetail(candidateDraftId)
    await loadAISuggestions()
    await loadConflicts()
  } catch (error) {
    candidateActionError.value = String(error?.userMessage || error?.message || '应用失败')
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
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿应用失败，请稍后重试')
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
    candidateActionError.value = String(error?.userMessage || error?.message || '候选版本切换失败，请稍后重试')
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
    candidateActionError.value = String(error?.userMessage || error?.message || '候选稿重写失败，请稍后重试')
  }
}

const handleApplyOutlineSuggestion = async (suggestionId) => {
  if (!suggestionId || outlineAssistStore.applySubmittingSuggestionId === suggestionId) return
  try {
    await outlineAssistStore.applySuggestion(suggestionId)
    ElMessage.success({
      message: '已应用 1 条建议',
      duration: 2000
    })
  } catch {}
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
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议审批失败，请稍后重试')
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
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议编辑审批失败，请稍后重试')
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
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议拒绝失败，请稍后重试')
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
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆建议暂缓失败，请稍后重试')
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
    ElMessage.success('记忆修订应用成功')
  } catch (error) {
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆修订应用失败')
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
    memoryActionError.value = String(error?.userMessage || error?.message || '记忆修订回滚失败，请稍后重试')
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
    traceActionError.value = String(error?.userMessage || error?.message || '追踪步骤加载失败')
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
    traceActionError.value = String(error?.userMessage || error?.message || '追踪详情加载失败')
  }
}

watch(() => props.workId, async () => {
  reindexActionError.value = ''
  clearReindexStartTimer()
  reindexPolling.stop()
  reindexPolling.jobId.value = ''
  reindexPolling.job.value = null
  reindexPolling.pollingHint.value = {}
  lastReindexRequest.value = null
  styleDNADraftText.value = ''
  styleDNASourceMode.value = 'user_upload'
  styleDNASelectedChapterIds.value = []
  autoQueueMode.value = 'safe'
  autoQueueTargetChapters.value = 5
  autoQueueTargetWordCount.value = 0
  autoQueueConflictSectionVisible.value = false
  autoQueueConflictLoading.value = false
  openingWizardVisible.value = false
  await autoQueueStore.initializeForWork(props.workId)
  await outlineAssistStore.initializeForWork(props.workId)
  syncAutoQueueDraftsFromStore()
  await openingStore.initializeForWork(props.workId)
  openingInitialLoading.value = true
  try {
    await openingStore.loadOpeningSnapshot(props.workId)
  } finally {
    openingInitialLoading.value = false
  }
  await styleDNAStore.initializeForWork(props.workId)
  await refreshPanel()
  await restorePendingVectorReindex()
}, { immediate: true })

watch(aiHelperViews, (views) => {
  const firstViewId = String(views[0]?.id || '')
  if (!views.some((item) => item.id === aiHelperActiveView.value)) {
    aiHelperActiveView.value = firstViewId
  }
}, { immediate: true })

watch(aiHelperActiveView, async (viewId) => {
  if (viewId === 'outline_assist' && outlineAssistEnabled) {
    await loadAISuggestions()
  }
})

watch(() => props.chapterId, async () => {
  autoQueueConflictSectionVisible.value = false
  autoQueueConflictLoading.value = false
  if (isReviewMode.value) {
    await refreshReviewPanel()
    return
  }
  const tasks = [
    loadContextReadiness(),
    loadAgentSessions(),
    loadPlotArcs(),
    loadPlanningData()
  ]
  if (outlineAssistEnabled && aiHelperActiveView.value === 'outline_assist') {
    tasks.push(loadAISuggestions())
  } else {
    outlineAssistStore.clearChapterScopedUiState()
  }
  await Promise.all(tasks)
}, { immediate: true })

watch(() => String(reindexPolling.job.value?.status || ''), async (status) => {
  if (!status || !TERMINAL_JOB_STATUSES.has(status)) return
  clearReindexStartTimer()
  clearPendingReindexRequest()
  if (status === 'completed' || status === 'partial_success') {
    reindexActionError.value = ''
    await loadContextReadiness()
    return
  }
  if (status === 'failed' && !reindexActionError.value) {
    reindexActionError.value = '索引重建失败，可以重试。'
  }
  if (status === 'cancelled' && !reindexActionError.value) {
    reindexActionError.value = '索引重建已取消。'
  }
})

watch(() => [autoQueueStore.config?.queue_mode, autoQueueStore.config?.target_chapters], () => {
  syncAutoQueueDraftsFromStore()
})
</script>

<style scoped>
.ai-panel {
  --ai-bg: var(--studio-card-bg, var(--ink-surface-1));
  --ai-bg-soft: var(--studio-bg-focus, var(--ink-surface-2));
  --ai-border: var(--studio-border, var(--ink-border));
  --ai-title: var(--studio-title, var(--ink-text-primary));
  --ai-text: var(--studio-text, var(--ink-text-secondary));
  --ai-muted: var(--studio-muted, var(--ink-text-muted));
  --ai-danger: var(--ink-danger-text);
  --ai-warning-bg: var(--ink-warning-bg);
  --ai-warning-text: var(--ink-warning-text);
  --ai-danger-bg: var(--ink-danger-bg);

  display: grid;
  gap: 14px;
  border: 1px solid var(--ai-border);
  border-radius: 20px;
  background: var(--ai-bg);
  padding: 16px;
  min-width: 0;
  min-height: 0;
}

.ai-panel-header h3,
.ai-section h4 {
  margin: 0;
  color: var(--ai-title);
}

.ai-panel-header p,
.ai-note,
.ai-error {
  margin: 6px 0 0;
  color: var(--ai-text);
  font-size: 13px;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.ai-error {
  color: var(--ai-danger);
}

.ai-section {
  display: grid;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid color-mix(in srgb, var(--ai-border) 62%, transparent);
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
  border: 1px solid color-mix(in srgb, var(--ai-warning-text) 45%, transparent);
  background: var(--ai-warning-bg);
  color: var(--ai-warning-text);
}

.conflict-banner-blocking {
  border: 1px solid color-mix(in srgb, var(--ai-danger) 45%, transparent);
  background: var(--ai-danger-bg);
  color: var(--ai-danger);
}

.settings-block-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--ai-warning-text) 45%, transparent);
  background: var(--ai-warning-bg);
  color: var(--ai-warning-text);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
}

.ai-actions,
.ai-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.ai-helper-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-helper-tab {
  border: 1px solid var(--ai-border);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--ai-title);
  background: var(--ai-bg-soft);
  cursor: pointer;
}

.ai-helper-tab--active {
  border-color: color-mix(in srgb, var(--ink-accent, #2563eb) 70%, white);
  background: color-mix(in srgb, var(--ink-accent-soft, #dbeafe) 65%, white);
  color: var(--ink-accent, #2563eb);
  font-weight: 600;
}

.opening-preview-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.opening-preview-card {
  display: grid;
  gap: 6px;
  border: 1px solid var(--ai-border);
  border-radius: 12px;
  background: var(--ai-bg-soft);
  padding: 12px;
  font-size: 13px;
  color: var(--ai-text);
}

.opening-preview-card strong {
  color: var(--ai-title);
}

.outline-apply-confirm {
  display: grid;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--ink-accent, #2563eb) 35%, var(--ai-border));
  border-radius: 12px;
  background: color-mix(in srgb, var(--ink-accent-soft, #dbeafe) 35%, var(--ai-bg));
  padding: 12px;
  font-size: 12px;
  color: var(--ai-text);
}

.outline-apply-confirm strong {
  color: var(--ai-title);
}

.ai-actions button,
.field-grid input,
.field-grid select {
  border: 1px solid var(--ai-border);
  border-radius: 999px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--ai-title);
  background: var(--ai-bg-soft);
}

.ai-actions button {
  cursor: pointer;
}
.ai-actions button:disabled {
  opacity: 0.4;
}

.tag {
  border: 1px solid var(--ink-accent-soft);
  background: color-mix(in srgb, var(--ink-accent-soft) 72%, var(--ai-bg));
  color: var(--ink-accent);
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
  overflow-wrap: anywhere;
  word-break: break-word;
}

.candidate-detail,
.quick-trial-output {
  white-space: pre-wrap;
  border-radius: 12px;
  background: var(--ai-bg-soft);
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
  border: 1px solid var(--ai-border);
  border-radius: 14px;
  padding: 12px;
  background: var(--ai-bg-soft);
}

.ai-field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: var(--ai-text);
}
</style>

