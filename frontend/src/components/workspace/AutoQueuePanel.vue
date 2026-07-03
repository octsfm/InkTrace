<template>
  <div v-if="featureEnabled" class="auto-queue-panel" data-test="auto-queue-panel">
    <div class="auto-queue-panel__header">
      <div>
        <h4>自动续写</h4>
        <p>为当前作品配置自动续写队列；安全模式逐章确认，连续模式在通过审稿后自动推进。</p>
      </div>
      <button
        data-test="auto-queue-refresh"
        type="button"
        :disabled="loading || savingConfig || actionLoading"
        @click="$emit('refresh')"
      >
        刷新
      </button>
    </div>

    <div v-if="aiSettingsBlocked" class="auto-queue-panel__banner auto-queue-panel__banner--warning">
      <strong>AI 设置未完成</strong>
      <span>请先配置可用模型服务与任务模型，再启动自动续写。</span>
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
        :class="{ 'auto-queue-panel__mode-button--active': queueMode === 'safe' }"
        :disabled="savingConfig || actionLoading"
        @click="$emit('update:queue-mode', 'safe')"
      >
        安全模式
      </button>
      <button
        data-test="auto-queue-mode-continuous"
        type="button"
        :class="{ 'auto-queue-panel__mode-button--active': queueMode === 'continuous' }"
        :disabled="savingConfig || actionLoading"
        @click="$emit('update:queue-mode', 'continuous')"
      >
        连续模式
      </button>
    </div>

    <p class="auto-queue-panel__hint">
      {{ queueMode === 'safe' ? '安全模式：每章完成后暂停，等你确认后继续。' : '连续模式：审稿通过后自动继续，但遇到 blocking 仍会暂停。' }}
    </p>

    <label class="auto-queue-panel__field">
      <span>目标章节数</span>
      <input
        data-test="auto-queue-target-chapters"
        type="number"
        min="1"
        max="10"
        :value="targetChapters"
        :disabled="savingConfig || actionLoading"
        @input="emitTargetChapters($event.target.value)"
      />
    </label>

    <div class="auto-queue-panel__actions">
      <button
        data-test="auto-queue-save-config"
        type="button"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canSubmitConfig"
        @click="$emit('save-config')"
      >
        {{ savingConfig ? '保存中…' : '保存设置' }}
      </button>
      <button
        data-test="auto-queue-start"
        type="button"
        :disabled="aiSettingsBlocked || savingConfig || actionLoading || !canStart"
        @click="$emit('start')"
      >
        {{ actionLoading && !currentRun?.run_id ? '启动中…' : '开始自动续写' }}
      </button>
      <button
        v-if="showPause"
        data-test="auto-queue-pause"
        type="button"
        :disabled="actionLoading"
        @click="$emit('pause')"
      >
        暂停
      </button>
      <button
        v-if="showResume"
        data-test="auto-queue-resume"
        type="button"
        :disabled="actionLoading"
        @click="$emit('resume')"
      >
        恢复
      </button>
      <button
        v-if="showConfirmContinue"
        data-test="auto-queue-confirm-continue"
        type="button"
        class="auto-queue-panel__primary"
        :disabled="actionLoading"
        @click="$emit('confirm-continue')"
      >
        确认后继续
      </button>
      <button
        v-if="showStop"
        data-test="auto-queue-stop"
        type="button"
        class="auto-queue-panel__danger"
        :disabled="actionLoading"
        @click="$emit('stop')"
      >
        停止队列
      </button>
    </div>

    <div v-if="showDisableBudgetCheck" class="auto-queue-panel__follow-up-actions">
      <button
        data-test="auto-queue-disable-budget-check"
        type="button"
        class="auto-queue-panel__danger"
        :disabled="actionLoading || savingConfig"
        @click="$emit('disable-budget-check')"
      >
        关闭预算检查
      </button>
    </div>

    <div v-if="showViewConflicts" class="auto-queue-panel__follow-up-actions">
      <button
        data-test="auto-queue-view-conflicts"
        type="button"
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
      <p class="auto-queue-panel__summary">
        {{ summaryCopy }}
      </p>
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
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  featureEnabled: {
    type: Boolean,
    default: false
  },
  aiSettingsBlocked: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  savingConfig: {
    type: Boolean,
    default: false
  },
  actionLoading: {
    type: Boolean,
    default: false
  },
  chapterId: {
    type: String,
    default: ''
  },
  queueMode: {
    type: String,
    default: 'safe'
  },
  targetChapters: {
    type: Number,
    default: 0
  },
  currentRun: {
    type: Object,
    default: null
  },
  historyRuns: {
    type: Array,
    default: () => []
  },
  errorMessage: {
    type: String,
    default: ''
  },
  noteMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'update:queue-mode',
  'update:target-chapters',
  'save-config',
  'start',
  'pause',
  'resume',
  'stop',
  'confirm-continue',
  'disable-budget-check',
  'view-conflicts',
  'refresh',
  'select-run'
])

const normalizedTargetChapters = computed(() => Math.max(0, Number(props.targetChapters || 0)))
const canSubmitConfig = computed(() => normalizedTargetChapters.value > 0)
const canStart = computed(() => canSubmitConfig.value && Boolean(props.chapterId))
const generatedCount = computed(() => Number(props.currentRun?.generated_count || 0))
const showPause = computed(() => String(props.currentRun?.status || '') === 'running')
const showResume = computed(() => String(props.currentRun?.status || '') === 'paused')
const showConfirmContinue = computed(() => String(props.currentRun?.status || '') === 'waiting_user_decision')
const showStop = computed(() => ['running', 'paused', 'waiting_user_decision'].includes(String(props.currentRun?.status || '')))
const showDisableBudgetCheck = computed(() => String(props.currentRun?.stop_record?.stop_reason || '') === 'budget_exceeded')
const showViewConflicts = computed(() => String(props.currentRun?.stop_record?.stop_reason || '') === 'blocking_review_consecutive')
const displayNote = computed(() => props.noteMessage || stopRecordCopy(props.currentRun?.stop_record))
const bannerModifierClass = computed(() => {
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (reason === 'budget_exceeded') return 'auto-queue-panel__banner--error'
  if (showConfirmContinue.value) return 'auto-queue-panel__banner--info'
  return 'auto-queue-panel__banner--warning'
})
const budgetUsageCopy = computed(() => {
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (reason !== 'budget_exceeded') return ''
  const consumedTokens = Number(props.currentRun?.consumed_tokens || 0)
  if (consumedTokens <= 0) return ''
  return `已使用约 ${consumedTokens} tokens`
})
const noteTitle = computed(() => {
  const reason = String(props.currentRun?.stop_record?.stop_reason || '')
  if (reason === 'budget_exceeded') return '预算已超出'
  if (reason === 'blocking_review_consecutive') return '连续出现严重冲突'
  if (reason === 'user_manual_stop') return '你已手动停止队列'
  if (showConfirmContinue.value) return '等待你确认'
  return '提示'
})
const summaryCopy = computed(() => {
  const status = String(props.currentRun?.status || '')
  if (status === 'waiting_user_decision') {
    return `当前队列在安全模式下暂停，已生成 ${generatedCount.value} 章候选稿，等待你确认后继续。`
  }
  if (status === 'running') {
    return `当前队列正在运行，已生成 ${generatedCount.value} 章候选稿。`
  }
  if (status === 'paused') {
    return `当前队列已暂停，已生成 ${generatedCount.value} 章候选稿。`
  }
  if (status === 'stopped') {
    return `当前队列已停止，已生成 ${generatedCount.value} 章候选稿，候选稿会保留在候选稿区。`
  }
  return `当前队列状态为 ${statusLabel(status)}。`
})

const modeLabel = (value) => ({
  safe: '安全模式',
  continuous: '连续模式'
}[String(value || '')] || String(value || '-'))

const statusLabel = (value) => ({
  idle: '未启动',
  pending: '待启动',
  running: '进行中',
  paused: '已暂停',
  waiting_user_decision: '等待你确认',
  stopped: '已停止',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消'
}[String(value || '')] || String(value || '-'))

const generatedCountLabel = (value) => `已生成 ${Number(value || 0)} 章候选稿`

const stopRecordCopy = (stopRecord) => {
  const reason = String(stopRecord?.stop_reason || '')
  if (reason === 'budget_exceeded') {
    return '预算已超出，自动续写已暂停。'
  }
  if (reason === 'blocking_review_consecutive') {
    return '连续出现严重冲突，自动续写已停止。'
  }
  if (reason === 'user_manual_stop') {
    return '你已手动停止队列，已生成候选稿会保留。'
  }
  return ''
}

const historyItemClass = (run) => ({
  'auto-queue-panel__history-item': true,
  'auto-queue-panel__history-item--current': String(run?.run_id || '') === String(props.currentRun?.run_id || '')
})

const emitTargetChapters = (value) => {
  const nextValue = Number.parseInt(String(value || '0'), 10)
  if (!Number.isFinite(nextValue)) {
    return
  }
  const normalized = Math.min(Math.max(nextValue, 0), 10)
  emit('update:target-chapters', normalized)
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

.auto-queue-panel__mode {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.auto-queue-panel__mode-button--active {
  background: var(--ai-bg-soft, #f1f5f9);
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
  background: color-mix(in srgb, var(--ai-warning-bg, #fff7ed) 85%, white);
}

.auto-queue-panel__banner--error {
  background: color-mix(in srgb, var(--ai-danger-bg, #fef2f2) 85%, white);
}

.auto-queue-panel__banner--info {
  background: color-mix(in srgb, var(--ai-accent-soft, #dbeafe) 60%, white);
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
  background: color-mix(in srgb, var(--ai-accent-soft, #dbeafe) 40%, white);
}

.auto-queue-panel__status-pill {
  border-radius: 999px;
  padding: 2px 8px;
  background: var(--ai-bg, #ffffff);
  border: 1px solid var(--ai-border, #d1d5db);
  font-size: 12px;
  color: var(--ai-text, #4b5563);
}

.auto-queue-panel__danger {
  color: var(--ink-danger-text, #b91c1c);
}

.auto-queue-panel__primary {
  background: var(--ai-accent, #2563eb);
  color: #ffffff;
  border-color: var(--ai-accent, #2563eb);
  font-weight: 600;
}
</style>
