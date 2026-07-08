<template>
  <div v-if="featureEnabled" class="auto-queue-panel" data-test="auto-queue-panel">
    <div class="auto-queue-panel__header">
      <div>
        <h4>自动续写</h4>
        <p>为当前作品配置自动续写队列;安全模式逐章确认,连续模式在通过审阅后自动推进。</p>
      </div>
      <button
        data-test="auto-queue-refresh"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="loading || savingConfig || actionLoading"
        @click="$emit('refresh')"
      >
        刷新
      </button>
    </div>

    <div v-if="aiSettingsBlocked" class="auto-queue-panel__banner auto-queue-panel__banner--warning">
      <strong>AI 设置未完成</strong>
      <span>请先配置可用模型服务与任务模型,再启动自动续写。</span>
    </div>

    <div v-else-if="errorMessage" class="auto-queue-panel__banner auto-queue-panel__banner--error">
      <strong>处理失败</strong>
      <span>{{ errorMessage }}</span>
    </div>

    <div
      v-else-if="displayNote"
      data-test="auto-queue-banner"
      class="auto-queue-panel__banner"
      :class="bannerModifierClass"
    >
      <strong>{{ noteTitle }}</strong>
      <span>{{ displayNote }}</span>
      <span v-if="budgetUsageCopy">{{ budgetUsageCopy }}</span>
    </div>

    <div class="auto-queue-panel__mode">
      <button
        data-test="auto-queue-mode-safe"
        type="button"
        class="ink-button"
        :class="queueMode === 'safe' ? 'ink-button--primary auto-queue-panel__mode-button--active' : 'ink-button--ghost'"
        :disabled="savingConfig || actionLoading"
        @click="$emit('update:queue-mode', 'safe')"
      >
        安全模式
      </button>
      <button
        data-test="auto-queue-mode-continuous"
        type="button"
        class="ink-button"
        :class="queueMode === 'continuous' ? 'ink-button--primary auto-queue-panel__mode-button--active' : 'ink-button--ghost'"
        :disabled="savingConfig || actionLoading"
        @click="$emit('update:queue-mode', 'continuous')"
      >
        连续模式
      </button>
    </div>

    <p class="auto-queue-panel__hint">
      {{ queueMode === 'safe' ? '安全模式:每章完成后暂停,等你确认后继续。' : '连续模式:审阅通过后自动继续,但遇到阻断冲突仍会暂停。' }}
    </p>

    <label class="auto-queue-panel__field">
      <span>目标章节数</span>
      <input
        data-test="auto-queue-target-chapters"
        type="number"
        min="0"
        max="10"
        :value="targetChapters"
        :disabled="savingConfig || actionLoading"
        @input="emitTargetChapters($event.target.value)"
      />
    </label>

    <label class="auto-queue-panel__field">
      <span>目标字数</span>
      <input
        data-test="auto-queue-target-words"
        type="number"
        min="0"
        step="1000"
        :value="targetWordCount"
        :disabled="savingConfig || actionLoading"
        @input="emitTargetWordCount($event.target.value)"
      />
    </label>

    <label class="auto-queue-panel__field">
      <span>预算上限令牌</span>
      <input
        ref="budgetLimitInputRef"
        data-test="auto-queue-budget-limit"
        type="number"
        min="0"
        step="1000"
        :value="budgetLimitTokens"
        :disabled="savingConfig || actionLoading"
        @input="emitBudgetLimitTokens($event.target.value)"
      />
    </label>

    <div class="auto-queue-panel__toggles">
      <label class="auto-queue-panel__toggle">
        <input
          data-test="auto-queue-stop-sequence-end"
          type="checkbox"
          :checked="stopAtSequenceEnd"
          :disabled="savingConfig || actionLoading"
          @change="emit('update:stop-at-sequence-end', $event.target.checked)"
        />
        <span>剧情波次结束时停止</span>
      </label>
      <label class="auto-queue-panel__toggle">
        <input
          data-test="auto-queue-stop-blocking-review"
          type="checkbox"
          :checked="stopOnBlockingReview"
          :disabled="savingConfig || actionLoading"
          @change="emit('update:stop-on-blocking-review', $event.target.checked)"
        />
        <span>连续出现阻断冲突时停止</span>
      </label>
      <label class="auto-queue-panel__toggle">
        <input
          data-test="auto-queue-stop-budget"
          type="checkbox"
          :checked="stopOnBudgetExceeded"
          :disabled="savingConfig || actionLoading"
          @change="emit('update:stop-on-budget-exceeded', $event.target.checked)"
        />
        <span>超预算时停止</span>
      </label>
      <label class="auto-queue-panel__toggle">
        <input
          data-test="auto-queue-stop-foreshadow"
          type="checkbox"
          :checked="stopOnForeshadowPremature"
          :disabled="savingConfig || actionLoading"
          @change="emit('update:stop-on-foreshadow-premature', $event.target.checked)"
        />
        <span>伏笔提前回收时停止</span>
      </label>
    </div>

    <div class="auto-queue-panel__actions">
      <button
        data-test="auto-queue-save-config"
        type="button"
        class="ink-button ink-button--secondary"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canSubmitConfig"
        @click="$emit('save-config')"
      >
        {{ savingConfig ? '保存中...' : '保存设置' }}
      </button>
      <button
        data-test="auto-queue-start"
        type="button"
        class="ink-button ink-button--primary"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canStart"
        @click="$emit('start')"
      >
        {{ actionLoading && !currentRun?.run_id ? '启动中...' : '开始自动续写' }}
      </button>
      <button
        v-if="showPause"
        data-test="auto-queue-pause"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="actionLoading"
        @click="$emit('pause')"
      >
        暂停
      </button>
      <button
        v-if="showResume"
        data-test="auto-queue-resume"
        type="button"
        class="ink-button ink-button--primary"
        :disabled="actionLoading"
        @click="$emit('resume')"
      >
        恢复
      </button>
      <button
        v-if="showContinueQueue"
        data-test="auto-queue-continue"
        type="button"
        class="ink-button ink-button--primary auto-queue-panel__primary"
        :disabled="actionLoading"
        @click="$emit('resume')"
      >
        继续队列
      </button>
      <button
        v-if="showConfirmContinue"
        data-test="auto-queue-confirm-continue"
        type="button"
        class="ink-button ink-button--primary auto-queue-panel__primary"
        :disabled="actionLoading"
        @click="$emit('confirm-continue')"
      >
        确认后继续
      </button>
      <button
        v-if="showStop"
        data-test="auto-queue-stop"
        type="button"
        class="ink-button ink-button--danger auto-queue-panel__danger"
        :disabled="actionLoading"
        @click="$emit('stop')"
      >
        停止队列
      </button>
    </div>

    <div v-if="showDisableBudgetCheck" class="auto-queue-panel__follow-up-actions">
      <button
        data-test="auto-queue-raise-budget"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="savingConfig || actionLoading"
        @click="focusBudgetLimitInput"
      >
        提高预算
      </button>
      <button
        data-test="auto-queue-disable-budget-check"
        type="button"
        class="ink-button ink-button--danger auto-queue-panel__danger"
        :disabled="actionLoading || savingConfig"
        @click="$emit('disable-budget-check')"
      >
        关闭预算检查
      </button>
    </div>

    <div v-if="showViewCandidates" class="auto-queue-panel__follow-up-actions">
      <button
        data-test="auto-queue-view-candidates"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="actionLoading || loading"
        @click="$emit('view-candidates')"
      >
        查看候选稿
      </button>
    </div>

    <div v-if="showViewConflicts" class="auto-queue-panel__follow-up-actions">
      <button
        data-test="auto-queue-view-conflicts"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="actionLoading || loading"
        @click="$emit('view-conflicts')"
      >
        查看冲突详情
      </button>
    </div>

    <div class="auto-queue-panel__meta">
      <span>当前模式 {{ modeLabel(currentRun?.queue_mode || queueMode) }}</span>
      <span>状态 {{ statusLabel(currentRun?.status || 'idle') }}</span>
      <span>已生成 {{ generatedCount }} 章候选稿</span>
    </div>

    <div v-if="currentRun" class="auto-queue-panel__card">
      <div class="auto-queue-panel__card-header">
        <strong>当前队列</strong>
        <span>{{ currentRun.run_id }}</span>
        <span class="auto-queue-panel__status-pill">{{ statusLabel(currentRun.status) }}</span>
      </div>
      <div
        v-if="progressVisible"
        class="auto-queue-panel__progress"
        data-test="auto-queue-progress"
      >
        <div class="auto-queue-panel__progress-copy">
          <strong>进度</strong>
          <span>{{ generatedCount }} / {{ progressTargetChapters }} 章</span>
        </div>
        <div class="auto-queue-panel__progress-track">
          <span class="auto-queue-panel__progress-fill" :style="{ width: `${progressPercent}%` }" />
        </div>
      </div>
      <div v-if="overviewMetrics.length" class="auto-queue-panel__overview">
        <div
          v-for="metric in overviewMetrics"
          :key="metric.label"
          class="auto-queue-panel__overview-item"
        >
          <strong>{{ metric.label }}</strong>
          <span>{{ metric.value }}</span>
        </div>
      </div>
      <p class="auto-queue-panel__summary">
        {{ summaryCopy }}
      </p>
      <div
        v-if="currentRunStopReasonCopy || currentRunSuggestedActionCopy"
        class="auto-queue-panel__stop-record"
        data-test="auto-queue-stop-record"
      >
        <span v-if="currentRunStopReasonCopy">停止原因:{{ currentRunStopReasonCopy }}</span>
        <span v-if="currentRunSuggestedActionCopy">建议操作:{{ currentRunSuggestedActionCopy }}</span>
      </div>
      <div
        v-if="perChapterItems.length"
        class="auto-queue-panel__chapters"
        data-test="auto-queue-per-chapter"
      >
        <strong>章节状态</strong>
        <ul>
          <li v-for="(item, index) in perChapterItems" :key="chapterItemKey(item, index)">
            <span>{{ chapterItemIcon(item.status) }}</span>
            <span>{{ chapterItemTitle(item, index) }}</span>
            <span v-if="Number(item.generated_word_count || 0) > 0">{{ formatCount(item.generated_word_count) }}字</span>
            <span>{{ chapterItemStatusLabel(item.status) }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="historyRuns.length" class="auto-queue-panel__history">
      <strong>历史记录</strong>
      <ul>
        <li v-for="run in historyRuns" :key="run.run_id">
          <button
            :data-test="`auto-queue-history-${run.run_id}`"
            type="button"
            :class="historyItemClass(run)"
            @click="$emit('select-run', run.run_id)"
          >
            <span>{{ run.run_id }}</span>
            <span>{{ statusLabel(run.status) }}</span>
            <span>{{ generatedCountLabel(run.generated_count) }}</span>
            <span v-if="historyStopReasonCopy(run)" class="auto-queue-panel__history-detail">{{ historyStopReasonCopy(run) }}</span>
            <span v-if="historySuggestedActionCopy(run)" class="auto-queue-panel__history-detail">{{ historySuggestedActionCopy(run) }}</span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  featureEnabled: { type: Boolean, default: false },
  aiSettingsBlocked: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  savingConfig: { type: Boolean, default: false },
  actionLoading: { type: Boolean, default: false },
  chapterId: { type: String, default: '' },
  queueMode: { type: String, default: 'safe' },
  targetChapters: { type: Number, default: 0 },
  targetWordCount: { type: Number, default: 0 },
  budgetLimitTokens: { type: Number, default: 0 },
  stopAtSequenceEnd: { type: Boolean, default: true },
  stopOnBlockingReview: { type: Boolean, default: true },
  stopOnBudgetExceeded: { type: Boolean, default: true },
  stopOnForeshadowPremature: { type: Boolean, default: true },
  currentRun: { type: Object, default: null },
  historyRuns: { type: Array, default: () => [] },
  errorMessage: { type: String, default: '' },
  noteMessage: { type: String, default: '' }
})

const emit = defineEmits([
  'update:queue-mode',
  'update:target-chapters',
  'update:target-word-count',
  'update:budget-limit-tokens',
  'update:stop-at-sequence-end',
  'update:stop-on-blocking-review',
  'update:stop-on-budget-exceeded',
  'update:stop-on-foreshadow-premature',
  'save-config',
  'start',
  'pause',
  'resume',
  'stop',
  'confirm-continue',
  'disable-budget-check',
  'view-candidates',
  'view-conflicts',
  'refresh',
  'select-run'
])

const budgetLimitInputRef = ref(null)
const normalizedTargetChapters = computed(() => Math.max(0, Number(props.targetChapters || 0)))
const normalizedTargetWordCount = computed(() => Math.max(0, Number(props.targetWordCount || 0)))
const normalizedBudgetLimitTokens = computed(() => Math.max(0, Number(props.budgetLimitTokens || 0)))
const hasNormalStopCondition = computed(() => (
  normalizedTargetChapters.value > 0 ||
  normalizedTargetWordCount.value > 0 ||
  Boolean(props.stopAtSequenceEnd) ||
  normalizedBudgetLimitTokens.value > 0
))
const canSubmitConfig = computed(() => {
  if (String(props.queueMode || 'safe') === 'continuous') {
    return normalizedTargetChapters.value > 0 || normalizedBudgetLimitTokens.value > 0
  }
  return hasNormalStopCondition.value
})
const canStart = computed(() => canSubmitConfig.value && Boolean(props.chapterId))
const generatedCount = computed(() => Number(props.currentRun?.generated_count || 0))
const showPause = computed(() => String(props.currentRun?.status || '') === 'running')
const showResume = computed(() => String(props.currentRun?.status || '') === 'paused')
const showContinueQueue = computed(() => String(props.currentRun?.status || '') === 'stopped')
const showConfirmContinue = computed(() => String(props.currentRun?.status || '') === 'waiting_user_decision')
const showStop = computed(() => ['running', 'paused', 'waiting_user_decision'].includes(String(props.currentRun?.status || '')))
const showViewCandidates = computed(() => {
  const status = String(props.currentRun?.status || '')
  return generatedCount.value > 0 && ['waiting_user_decision', 'completed', 'stopped'].includes(status)
})
const showDisableBudgetCheck = computed(() => String(props.currentRun?.stop_record?.stop_reason || '') === 'budget_exceeded')
const showViewConflicts = computed(() => String(props.currentRun?.stop_record?.stop_reason || '') === 'blocking_review_consecutive')
const displayNote = computed(() => {
  const status = String(props.currentRun?.status || '')
  if (status === 'running') return `正在生成第 ${generatedCount.value + 1} 章`
  if (status === 'stopping') return '正在停止,等待当前章节处理完成。'
  if (status === 'waiting_user_decision' && generatedCount.value > 0) return `第 ${generatedCount.value} 章已生成,需要你确认`
  if (status === 'completed') return '全部章节已生成'
  if (status === 'failed') return '当前队列执行失败,请检查停止原因或稍后重试。'
  if (status === 'cancelled') return '当前队列已取消,已生成候选稿会保留。'
  return props.noteMessage || stopRecordCopy(props.currentRun?.stop_record)
})
const bannerModifierClass = computed(() => {
  const status = String(props.currentRun?.status || '')
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (status === 'failed') return 'auto-queue-panel__banner--error'
  if (status === 'stopping') return 'auto-queue-panel__banner--warning'
  if (reason === 'budget_exceeded') return 'auto-queue-panel__banner--error'
  if (showConfirmContinue.value) return 'auto-queue-panel__banner--info'
  return 'auto-queue-panel__banner--warning'
})
const budgetUsageCopy = computed(() => {
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (reason !== 'budget_exceeded') return ''
  const consumedTokens = Number(props.currentRun?.consumed_tokens || 0)
  const budgetLimit = normalizedBudgetLimitTokens.value
  if (consumedTokens <= 0 && budgetLimit <= 0) return ''
  if (budgetLimit > 0) return `已使用约 ${consumedTokens} / 预算 ${budgetLimit} 令牌`
  return `已使用约 ${consumedTokens} 令牌`
})
const noteTitle = computed(() => {
  const status = String(props.currentRun?.status || '')
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (status === 'running') return '正在生成'
  if (status === 'stopping') return '正在停止'
  if (status === 'waiting_user_decision') return '当前章节需要你确认'
  if (status === 'completed') return '自动续写已完成'
  if (status === 'failed') return '执行失败'
  if (status === 'cancelled') return '已取消'
  if (reason === 'budget_exceeded') return '预算已超出'
  if (reason === 'blocking_review_consecutive') return '连续出现严重冲突'
  if (reason === 'user_manual_stop') return '你已手动停止队列'
  if (showConfirmContinue.value) return '等待你确认'
  return '提示'
})
const summaryCopy = computed(() => {
  const status = String(props.currentRun?.status || '')
  if (status === 'waiting_user_decision') return `当前队列在安全模式下暂停,已生成 ${generatedCount.value} 章候选稿,等待你确认后继续。`
  if (status === 'running') return `当前队列正在运行,已生成 ${generatedCount.value} 章候选稿。`
  if (status === 'paused') return `当前队列已暂停,已生成 ${generatedCount.value} 章候选稿。`
  if (status === 'stopped') return `当前队列已停止,已生成 ${generatedCount.value} 章候选稿,候选稿会保留在候选稿区。`
  if (status === 'stopping') return '当前队列正在停止,等待当前章节处理完成后结束。'
  if (status === 'completed') return `当前队列已完成,累计生成 ${generatedCount.value} 章候选稿。`
  if (status === 'failed') return '当前队列执行失败,请检查停止原因或稍后重试。'
  if (status === 'cancelled') return '当前队列已取消,已生成候选稿会保留。'
  return `当前队列状态为 ${statusLabel(status)}。`
})
const progressTargetChapters = computed(() => Number(props.currentRun?.target_chapters || props.targetChapters || 0))
const progressVisible = computed(() => progressTargetChapters.value > 0 && Boolean(props.currentRun))
const progressPercent = computed(() => {
  if (progressTargetChapters.value <= 0) return 0
  const explicitPercent = Number(props.currentRun?.progress_percent || 0)
  if (explicitPercent > 0) return Math.min(100, Math.max(0, explicitPercent))
  return Math.min(100, Math.max(0, Math.round((generatedCount.value / progressTargetChapters.value) * 100)))
})
const overviewMetrics = computed(() => {
  const items = []
  const totalWords = Number(props.currentRun?.total_word_count || 0)
  const targetWords = Number(props.currentRun?.target_word_count || props.targetWordCount || 0)
  const consumedTokens = Number(props.currentRun?.consumed_tokens || 0)
  if (totalWords > 0 || targetWords > 0) {
    items.push({ label: '字数', value: `${formatCount(totalWords)}${targetWords > 0 ? ` / ${formatCount(targetWords)}` : ''}` })
  }
  if (consumedTokens > 0) {
    items.push({ label: '令牌', value: formatTokenCount(consumedTokens) })
  }
  return items
})
const perChapterItems = computed(() => Array.isArray(props.currentRun?.per_chapter) ? props.currentRun.per_chapter : [])
const currentRunStopReasonCopy = computed(() => stopReasonLabel(props.currentRun?.stop_record))
const currentRunSuggestedActionCopy = computed(() => suggestedActionLabel(props.currentRun?.stop_record))

const modeLabel = (value) => ({ safe: '安全模式', continuous: '连续模式' }[String(value || '')] || String(value || '-'))
const statusLabel = (value) => ({ idle: '未启动', pending: '待启动', running: '进行中', paused: '已暂停', stopping: '正在停止', waiting_user_decision: '等待你确认', stopped: '已停止', completed: '已完成', failed: '失败', cancelled: '已取消' }[String(value || '')] || String(value || '-'))
const generatedCountLabel = (value) => `已生成 ${Number(value || 0)} 章候选稿`
const formatCount = (value) => Number(value || 0).toLocaleString('zh-CN')
const formatTokenCount = (value) => {
  const normalized = Number(value || 0)
  return normalized >= 1000 ? `${Math.round(normalized / 1000)}K` : `${normalized}`
}
const chapterItemKey = (item, index) => item?.chapter_id || item?.chapter_title || `chapter_${index}`
const chapterItemTitle = (item, index) => String(item?.chapter_title || item?.chapter_name || `第${index + 1}章`)
const chapterItemIcon = (status) => ({ review_passed: '✓', candidate_generation: '📝', waiting: '⏳', waiting_user_decision: '⏳', running: '📝', completed: '✓' }[String(status || '')] || '•')
const chapterItemStatusLabel = (status) => ({ review_passed: '审阅通过', candidate_generation: '生成中', waiting: '等待中', waiting_user_decision: '等待确认', running: '进行中', completed: '已完成', blocked: '阻断' }[String(status || '')] || statusLabel(status))

const stopRecordCopy = (stopRecord) => {
  const reason = String(stopRecord?.stop_reason || '')
  if (reason === 'budget_exceeded') return '预算已超出,自动续写已暂停。'
  if (reason === 'blocking_review_consecutive') return '连续出现严重冲突,自动续写已停止。'
  if (reason === 'user_manual_stop') return '你已手动停止队列,已生成候选稿会保留。'
  return ''
}
const stopReasonLabel = (stopRecord) => {
  const reason = String(stopRecord?.stop_reason || '')
  if (reason === 'budget_exceeded') return '预算已超出'
  if (reason === 'blocking_review_consecutive') return '连续出现阻断冲突'
  if (reason === 'user_manual_stop') return '你已手动停止队列'
  if (reason === 'target_chapters_reached') return '已达到目标章节数'
  if (reason === 'target_words_reached') return '已达到目标字数'
  if (reason === 'sequence_arc_ended') return '已到达剧情波次结束点'
  return ''
}
const suggestedActionLabel = (stopRecord) => {
  const action = String(stopRecord?.suggested_action || '')
  if (action === 'adjust_budget') return '提高预算或关闭预算检查'
  if (action === 'resolve_conflict') return '先查看并处理冲突详情'
  if (action === 'resume_queue') return '处理原因后继续队列'
  if (action === 'manual_continue') return '确认后手动继续'
  return ''
}
const historyStopReasonCopy = (run) => stopReasonLabel(run?.stop_record)
const historySuggestedActionCopy = (run) => suggestedActionLabel(run?.stop_record)
const focusBudgetLimitInput = () => budgetLimitInputRef.value?.focus()
const historyItemClass = (run) => ({ 'auto-queue-panel__history-item': true, 'auto-queue-panel__history-item--current': String(run?.run_id || '') === String(props.currentRun?.run_id || '') })
const emitTargetChapters = (value) => {
  const nextValue = Number.parseInt(String(value || '0'), 10)
  if (!Number.isFinite(nextValue)) return
  emit('update:target-chapters', Math.min(Math.max(nextValue, 0), 10))
}
const emitTargetWordCount = (value) => {
  const nextValue = Number.parseInt(String(value || '0'), 10)
  if (!Number.isFinite(nextValue)) return
  emit('update:target-word-count', Math.max(nextValue, 0))
}
const emitBudgetLimitTokens = (value) => {
  const nextValue = Number.parseInt(String(value || '0'), 10)
  if (!Number.isFinite(nextValue)) return
  emit('update:budget-limit-tokens', Math.max(nextValue, 0))
}
</script>

<style scoped>
.auto-queue-panel {
  display: grid;
  gap: 12px;
}

.auto-queue-panel__header,
.auto-queue-panel__card-header,
.auto-queue-panel__meta,
.auto-queue-panel__actions,
.auto-queue-panel__follow-up-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.auto-queue-panel__header h4,
.auto-queue-panel__history strong {
  margin: 0;
  color: var(--ai-title, #111827);
}

.auto-queue-panel__header p,
.auto-queue-panel__summary,
.auto-queue-panel__hint {
  margin: 4px 0 0;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__toggles {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.auto-queue-panel__toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__progress,
.auto-queue-panel__overview,
.auto-queue-panel__chapters,
.auto-queue-panel__stop-record {
  margin-top: 12px;
}

.auto-queue-panel__progress {
  display: grid;
  gap: 8px;
}

.auto-queue-panel__progress-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__progress-track {
  width: 100%;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ai-border, #d1d5db);
}

.auto-queue-panel__progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ai-accent, #2563eb);
}

.auto-queue-panel__overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}

.auto-queue-panel__overview-item {
  display: grid;
  gap: 4px;
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 12px;
  padding: 10px 12px;
  background: var(--ai-bg, #ffffff);
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__chapters {
  display: grid;
  gap: 8px;
}

.auto-queue-panel__stop-record {
  display: grid;
  gap: 6px;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__chapters ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.auto-queue-panel__chapters li {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 10px;
  padding: 8px 10px;
  background: var(--ai-bg, #ffffff);
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__mode {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.auto-queue-panel__mode-button--active {
  font-weight: 600;
}

.auto-queue-panel__field {
  display: grid;
  gap: 8px;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.auto-queue-panel__field input {
  width: 100%;
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  color: var(--ai-title, #111827);
  background: var(--ai-bg, #ffffff);
}

.auto-queue-panel__banner,
.auto-queue-panel__card,
.auto-queue-panel__history {
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 14px;
  padding: 12px;
  background: var(--ai-bg-soft, #f8fafc);
}

.auto-queue-panel__banner {
  display: grid;
  gap: 4px;
}

.auto-queue-panel__banner--warning {
  background: color-mix(in srgb, var(--ai-warning-bg, #fff7ed) 85%, var(--ai-bg, #ffffff));
}

.auto-queue-panel__banner--error {
  background: color-mix(in srgb, var(--ai-danger-bg, #fef2f2) 85%, var(--ai-bg, #ffffff));
}

.auto-queue-panel__banner--info {
  background: color-mix(in srgb, var(--ai-accent-soft, #dbeafe) 60%, var(--ai-bg, #ffffff));
}

.auto-queue-panel__history ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.auto-queue-panel__history-item {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 10px;
  padding: 8px 10px;
  background: var(--ai-bg, #ffffff);
  color: var(--ai-text, #4b5563);
  text-align: left;
}

.auto-queue-panel__history-item--current {
  border-color: var(--ai-accent, #3b82f6);
  background: color-mix(in srgb, var(--ai-accent-soft, #dbeafe) 40%, var(--ai-bg, #ffffff));
}

.auto-queue-panel__history-detail {
  width: 100%;
  color: var(--ai-text, #4b5563);
  font-size: 12px;
}

.auto-queue-panel__status-pill {
  border-radius: 999px;
  padding: 2px 8px;
  background: var(--ai-bg, #ffffff);
  border: 1px solid var(--ai-border, #d1d5db);
  font-size: 12px;
  color: var(--ai-text, #4b5563);
}
</style>
