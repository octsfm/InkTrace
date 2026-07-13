<template>
  <div v-if="featureEnabled" class="auto-queue-panel" data-test="auto-queue-panel">
    <div class="auto-queue-panel__header">
      <div>
        <h4>接着写</h4>
        <p>说想法 <span aria-hidden="true">→</span> 写一章 <span aria-hidden="true">→</span> 你来看 <span aria-hidden="true">→</span> 再决定</p>
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
      <span>请先完成 AI 设置，再请它接着写。</span>
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

    <section v-if="!currentRun" class="auto-queue-panel__intent" aria-labelledby="auto-queue-intent-title">
      <h5 id="auto-queue-intent-title">下一章，你最想看到什么？</h5>
      <div class="auto-queue-panel__intent-options">
        <button
          v-for="option in intentOptions"
          :key="option.id"
          :data-test="`auto-queue-intent-${option.id}`"
          type="button"
          class="auto-queue-panel__intent-option"
          :class="{ 'auto-queue-panel__intent-option--active': localWritingIntent === option.instruction }"
          :aria-pressed="localWritingIntent === option.instruction"
          :disabled="savingConfig || actionLoading"
          @click="chooseIntent(option.instruction)"
        >
          {{ option.label }}
        </button>
      </div>
      <label class="auto-queue-panel__intent-field">
        <span class="sr-only">下一章的想法</span>
        <textarea
          data-test="auto-queue-writing-intent"
          rows="3"
          maxlength="60"
          :value="localWritingIntent"
          :disabled="savingConfig || actionLoading"
          placeholder="或者写一句你自己的想法"
          @input="updateWritingIntent($event.target.value)"
        />
        <span class="auto-queue-panel__intent-count">{{ localWritingIntent.length }}/60</span>
      </label>
      <p class="auto-queue-panel__safety-note">
        <strong>只会写一份新稿，不会改动你的正文。</strong>
        <span>写完先给你看。</span>
      </p>
      <button
        data-test="auto-queue-start"
        type="button"
        class="ink-button ink-button--primary auto-queue-panel__start"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canStart"
        @click="$emit('start')"
      >
        {{ actionLoading ? '正在准备新稿…' : '写一章给我看' }}
      </button>
      <button
        data-test="auto-queue-start-direct"
        type="button"
        class="auto-queue-panel__direct-start"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canStart"
        @click="startDirectly"
      >
        不用补充，直接接着写
      </button>
    </section>

    <details class="auto-queue-panel__advanced">
      <summary>更多保护设置</summary>

    <div class="auto-queue-panel__mode" data-test="auto-queue-mode-per-chapter">
      <strong>每次只写一章</strong>
    </div>

    <p class="auto-queue-panel__hint">
      写完先停下来，等你看过再决定要不要继续。
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
      <span>本次 AI 用量上限</span>
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
        <span>连续发现严重矛盾时停下来</span>
      </label>
      <label class="auto-queue-panel__toggle">
        <input
          data-test="auto-queue-stop-budget"
          type="checkbox"
          :checked="stopOnBudgetExceeded"
          :disabled="savingConfig || actionLoading"
          @change="emit('update:stop-on-budget-exceeded', $event.target.checked)"
        />
        <span>到达用量上限时停下来</span>
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

      <button
        data-test="auto-queue-save-config"
        type="button"
        class="ink-button ink-button--secondary"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canSubmitConfig"
        @click="$emit('save-config')"
      >
        {{ savingConfig ? '保存中...' : '保存保护设置' }}
      </button>
    </details>

    <div class="auto-queue-panel__actions">
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
        处理好了，继续写
      </button>
      <button
        v-if="showConfirmContinue"
        data-test="auto-queue-confirm-continue"
        type="button"
        class="ink-button ink-button--primary auto-queue-panel__primary"
        :disabled="actionLoading"
        @click="$emit('confirm-continue')"
      >
        继续写下一章
      </button>
      <button
        v-if="showStop"
        data-test="auto-queue-stop"
        type="button"
        class="ink-button ink-button--danger auto-queue-panel__danger"
        :disabled="actionLoading"
        @click="$emit('stop')"
      >
        停下这次续写
      </button>
      <button
        v-if="showCancel"
        data-test="auto-queue-cancel"
        type="button"
        class="ink-button ink-button--danger auto-queue-panel__danger"
        :disabled="actionLoading"
        @click="$emit('cancel')"
      >
        放弃这次
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
      <span>每次只写一章</span>
      <span>状态 {{ statusLabel(currentRun?.status || 'idle') }}</span>
      <span>已生成 {{ generatedCount }} 章候选稿</span>
    </div>

    <div v-if="currentRun" class="auto-queue-panel__card">
      <div class="auto-queue-panel__card-header">
        <strong>这次接着写</strong>
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
                <span v-if="currentRunStopReasonCopy">停止原因：{{ currentRunStopReasonCopy }}</span>
        <span v-if="currentRunSuggestedActionCopy">建议操作：{{ currentRunSuggestedActionCopy }}</span>
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
            <span>以前写过的一次</span>
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
import { computed, ref, watch } from 'vue'

const props = defineProps({
  featureEnabled: { type: Boolean, default: false },
  aiSettingsBlocked: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  savingConfig: { type: Boolean, default: false },
  actionLoading: { type: Boolean, default: false },
  chapterId: { type: String, default: '' },
  writingIntent: { type: String, default: '' },
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
  'update:target-chapters',
  'update:writing-intent',
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
  'cancel',
  'confirm-continue',
  'disable-budget-check',
  'view-candidates',
  'view-conflicts',
  'refresh',
  'select-run'
])

const budgetLimitInputRef = ref(null)
const localWritingIntent = ref(String(props.writingIntent || '').slice(0, 60))
watch(() => props.writingIntent, (value) => {
  localWritingIntent.value = String(value || '').slice(0, 60)
})
const intentOptions = [
  {
    id: 'conflict',
    label: '让冲突更紧张',
    instruction: '下一章优先增强当前冲突，让局势更紧张，但不要提前解决核心矛盾。'
  },
  {
    id: 'relationship',
    label: '让人物关系推进',
    instruction: '下一章优先推进当前人物关系，让互动产生清晰变化，但不要改变既定人物性格。'
  },
  {
    id: 'foreshadow',
    label: '把刚才的伏笔接下去',
    instruction: '下一章优先承接最近出现且尚未解决的伏笔，但不要提前揭示不该揭示的信息。'
  }
]
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
  return hasNormalStopCondition.value
})
const canStart = computed(() => canSubmitConfig.value && Boolean(props.chapterId))
const generatedCount = computed(() => Number(props.currentRun?.generated_count || 0))
const showPause = computed(() => String(props.currentRun?.status || '') === 'running')
const showResume = computed(() => String(props.currentRun?.status || '') === 'paused')
const showContinueQueue = computed(() => String(props.currentRun?.status || '') === 'stopped')
const showConfirmContinue = computed(() => String(props.currentRun?.status || '') === 'waiting_user_decision')
const showStop = computed(() => ['running', 'paused', 'waiting_user_decision'].includes(String(props.currentRun?.status || '')))
const showCancel = computed(() => ['paused', 'waiting_user_decision', 'stopped'].includes(String(props.currentRun?.status || '')))
const showViewCandidates = computed(() => {
  const status = String(props.currentRun?.status || '')
  return generatedCount.value > 0 && ['waiting_user_decision', 'completed', 'stopped'].includes(status)
})
const showDisableBudgetCheck = computed(() => String(props.currentRun?.stop_record?.stop_reason || '') === 'budget_exceeded')
const showViewConflicts = computed(() => String(props.currentRun?.stop_record?.stop_reason || '') === 'blocking_review_consecutive')
const displayNote = computed(() => {
  const status = String(props.currentRun?.status || '')
  if (status === 'running') return `正在生成第 ${generatedCount.value + 1} 章`
  if (status === 'stopping') return '正在停止，等待当前章节处理完成。'
  if (status === 'waiting_user_decision' && generatedCount.value > 0) return `第 ${generatedCount.value} 章已生成，需要你确认`
  if (status === 'completed') return '全部章节已生成'
  if (status === 'failed') return '这次没有写完，请看看原因或稍后重试。'
  if (status === 'cancelled') return '这次续写已结束，已经写好的新稿会保留。'
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
  if (budgetLimit > 0) return `已使用约 ${consumedTokens} / 上限 ${budgetLimit} AI 用量`
  return `已使用约 ${consumedTokens} AI 用量`
})
const noteTitle = computed(() => {
  const status = String(props.currentRun?.status || '')
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (status === 'running') return '正在生成'
  if (status === 'stopping') return '正在停止'
  if (status === 'waiting_user_decision') return '当前章节需要你确认'
  if (status === 'completed') return '这次新稿写完了'
  if (status === 'failed') return '执行失败'
  if (status === 'cancelled') return '已取消'
  if (reason === 'budget_exceeded') return '预算已超出'
  if (reason === 'blocking_review_consecutive') return '连续出现严重冲突'
  if (reason === 'user_manual_stop') return '你已停下这次续写'
  if (showConfirmContinue.value) return '等待你确认'
  return '提示'
})
const summaryCopy = computed(() => {
  const status = String(props.currentRun?.status || '')
  if (status === 'waiting_user_decision') return `新写的一章还没有放进正文。已经写好 ${generatedCount.value} 章，等你看过再决定。`
  if (status === 'running') return `正在写新稿，已经写好 ${generatedCount.value} 章。`
  if (status === 'paused') return `已经停下来，写好的 ${generatedCount.value} 章新稿都还在。`
  if (status === 'stopped') return `这次续写已停下，写好的 ${generatedCount.value} 章新稿都还在。`
  if (status === 'stopping') return '正在停下来，写完手上这一章就结束。'
  if (status === 'completed') return `这次新稿写完了，共有 ${generatedCount.value} 章。`
  if (status === 'failed') return '这次没有写完，请看看原因或稍后重试。'
  if (status === 'cancelled') return '这次续写已结束，已经写好的新稿会保留。'
  return `这次续写：${statusLabel(status)}。`
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
    items.push({ label: 'AI 用量', value: formatTokenCount(consumedTokens) })
  }
  return items
})
const perChapterItems = computed(() => Array.isArray(props.currentRun?.per_chapter) ? props.currentRun.per_chapter : [])
const currentRunStopReasonCopy = computed(() => stopReasonLabel(props.currentRun?.stop_record))
const currentRunSuggestedActionCopy = computed(() => suggestedActionLabel(props.currentRun?.stop_record))

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
const chapterItemStatusLabel = (status) => ({ review_passed: '审阅通过', candidate_generation: '生成中', waiting: '等待中', waiting_user_decision: '等待确认', running: '进行中', completed: '已完成', blocked: '需要你处理' }[String(status || '')] || statusLabel(status))

const stopRecordCopy = (stopRecord) => {
  const reason = String(stopRecord?.stop_reason || '')
  if (reason === 'budget_exceeded') return '已到达你设置的用量上限，这次续写已停下。'
  if (reason === 'blocking_review_consecutive') return '连续发现需要你处理的矛盾，这次续写已停下。'
  if (reason === 'user_manual_stop') return '你已停下这次续写，写好的新稿会保留。'
  return ''
}
const stopReasonLabel = (stopRecord) => {
  const reason = String(stopRecord?.stop_reason || '')
  if (reason === 'budget_exceeded') return '预算已超出'
  if (reason === 'blocking_review_consecutive') return '连续发现需要你处理的矛盾'
  if (reason === 'user_manual_stop') return '你已停下这次续写'
  if (reason === 'target_chapters_reached') return '已达到目标章节数'
  if (reason === 'target_words_reached') return '已达到目标字数'
  if (reason === 'sequence_arc_ended') return '已到达剧情波次结束点'
  return ''
}
const suggestedActionLabel = (stopRecord) => {
  const action = String(stopRecord?.suggested_action || '')
  if (action === 'adjust_budget') return '提高预算或关闭预算检查'
  if (action === 'resolve_conflict') return '先查看并处理冲突详情'
  if (action === 'resume_queue') return '处理好原因后继续写'
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
const updateWritingIntent = (value) => {
  localWritingIntent.value = String(value || '').slice(0, 60)
  emit('update:writing-intent', localWritingIntent.value)
}
const chooseIntent = (instruction) => updateWritingIntent(instruction)
const startDirectly = () => {
  updateWritingIntent('')
  emit('start')
}
</script>

<style scoped>
.auto-queue-panel {
  display: grid;
  gap: 16px;
  color: var(--ai-title, #2d2926);
}

.auto-queue-panel__intent {
  display: grid;
  gap: 12px;
  border: 1px solid color-mix(in srgb, var(--ai-border, #d8cec0) 80%, #b58b58);
  border-radius: 16px;
  padding: 16px;
  background: color-mix(in srgb, var(--ai-bg, #fffdf8) 92%, #f4eadb);
}

.auto-queue-panel__intent h5 {
  margin: 0;
  font-family: ui-serif, "Songti SC", "STSong", serif;
  font-size: 17px;
  color: var(--ai-title, #2d2926);
}

.auto-queue-panel__intent-options {
  display: grid;
  gap: 8px;
}

.auto-queue-panel__intent-option {
  width: 100%;
  border: 1px solid var(--ai-border, #d8cec0);
  border-radius: 12px;
  padding: 10px 12px;
  background: var(--ai-bg, #fffdf8);
  color: var(--ai-title, #2d2926);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.auto-queue-panel__intent-option:hover,
.auto-queue-panel__intent-option--active {
  border-color: var(--ai-accent, #9b6b3d);
  background: color-mix(in srgb, var(--ai-accent-soft, #efe1cf) 55%, var(--ai-bg, #fffdf8));
}

.auto-queue-panel__intent-field {
  position: relative;
  display: block;
}

.auto-queue-panel__intent-field textarea {
  box-sizing: border-box;
  width: 100%;
  resize: vertical;
  border: 1px solid var(--ai-border, #d8cec0);
  border-radius: 12px;
  padding: 11px 12px 25px;
  background: var(--ai-bg, #fffdf8);
  color: var(--ai-title, #2d2926);
  font: inherit;
  line-height: 1.55;
}

.auto-queue-panel__intent-field textarea:focus-visible,
.auto-queue-panel__intent-option:focus-visible,
.auto-queue-panel__direct-start:focus-visible {
  outline: 2px solid var(--ai-accent, #9b6b3d);
  outline-offset: 2px;
}

.auto-queue-panel__intent-count {
  position: absolute;
  right: 10px;
  bottom: 8px;
  color: var(--ai-text, #756b62);
  font-size: 12px;
}

.auto-queue-panel__safety-note {
  display: grid;
  gap: 3px;
  margin: 0;
  border-left: 3px solid var(--ai-accent, #9b6b3d);
  padding-left: 10px;
  color: var(--ai-text, #625950);
  font-size: 13px;
  line-height: 1.5;
}

.auto-queue-panel__start {
  width: 100%;
  justify-content: center;
}

.auto-queue-panel__direct-start {
  border: 0;
  padding: 4px;
  background: transparent;
  color: var(--ai-text, #625950);
  font: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.auto-queue-panel__advanced {
  border-top: 1px solid var(--ai-border, #d8cec0);
  padding-top: 10px;
}

.auto-queue-panel__advanced summary {
  cursor: pointer;
  color: var(--ai-text, #625950);
  font-size: 13px;
}

.auto-queue-panel__advanced[open] {
  display: grid;
  gap: 12px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  clip-path: inset(50%);
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
