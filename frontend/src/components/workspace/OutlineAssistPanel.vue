<template>
  <div v-if="featureEnabled" class="outline-assist-panel" data-test="outline-assist-panel">
    <div class="ai-helper-view" data-test="outline-assist-view">
      <div class="outline-assist-header">
        <div>
          <h5>大纲辅助</h5>
          <p class="ai-note">先选一种整理方式，看看前后变化，再由你决定要不要使用。</p>
        </div>
        <button
          data-test="outline-assist-refresh"
          type="button"
          class="ink-button ink-button--ghost"
          :disabled="loading || targetLoading || generating || actionBusy"
          @click="$emit('refresh')"
        >
          {{ loading || targetLoading ? '刷新中...' : '重新读取大纲' }}
        </button>
      </div>

      <label class="outline-target-picker" for="outline-assist-target-select">
        <span>要整理哪里？</span>
        <select
          id="outline-assist-target-select"
          data-test="outline-assist-target-select"
          :value="targetSelection"
          :disabled="targetLoading || generating || actionBusy"
          @change="$emit('target-change', $event.target.value)"
        >
          <option value="work">整本故事大纲</option>
          <optgroup v-if="chapterOptions.length" label="某一章">
            <option
              v-for="(chapter, index) in chapterOptions"
              :key="chapter.id"
              :value="`chapter:${chapter.id}`"
            >
              {{ chapterTargetLabel(chapter, index) }}
            </option>
          </optgroup>
          <option value="selection">一段临时文字</option>
        </select>
      </label>
      <p class="outline-target-label" data-test="outline-assist-target">
        当前整理：<strong>{{ targetLabel }}</strong>
      </p>

      <div
        class="ai-helper-nav"
        data-test="outline-assist-mode-nav"
        role="tablist"
        aria-label="选择大纲整理方式"
      >
        <button
          v-for="mode in modes"
          :id="`outline-assist-tab-${mode.id}`"
          :key="mode.id"
          :data-test="`outline-assist-mode-${mode.id}`"
          type="button"
          role="tab"
          class="ai-helper-tab"
          :class="{ 'ai-helper-tab--active': activeMode === mode.id }"
          :aria-selected="activeMode === mode.id ? 'true' : 'false'"
          :aria-controls="`outline-assist-pane-${mode.id}`"
          :disabled="isModeDisabled(mode.id) || generating || targetLoading || actionBusy"
          @click="$emit('update:active-mode', mode.id)"
        >
          {{ mode.label }}
        </button>
      </div>
      <p
        v-if="targetKind !== 'chapter_outline'"
        class="ai-note"
        data-test="outline-chapter-mode-hint"
      >
        “生成本章细纲”和“整理本章写作要点”需要先选一章，我才能把内容放对位置。
      </p>

      <section
        :id="`outline-assist-pane-${activeMode}`"
        class="outline-source-card"
        role="tabpanel"
        :aria-labelledby="`outline-assist-tab-${activeMode}`"
      >
        <p class="ai-note">{{ activeModeHelp }}</p>
        <label for="outline-assist-source">
          {{ targetKind === 'selection' ? '想整理的临时文字' : '想让 AI 参考的这段大纲' }}
        </label>
        <textarea
          id="outline-assist-source"
          data-test="outline-assist-source"
          :value="sourceText"
          :disabled="targetLoading || generating || actionBusy"
          rows="6"
          :placeholder="targetKind === 'selection'
            ? '先写下想整理的文字。'
            : '大纲内容会自动放在这里，你也可以只保留想整理的那一段。'"
          @input="$emit('update:source-text', $event.target.value)"
        />
        <p v-if="isModeDisabled(activeMode)" class="ai-note">
          请先选定一个章节，再使用这个功能。
        </p>
        <p v-else-if="selectionTextMissing" class="ai-note" data-test="outline-selection-empty-hint">
          先写下想整理的文字。
        </p>
        <p v-else-if="!targetReady" class="ai-note">请先重新读取大纲。</p>
        <button
          data-test="outline-assist-generate"
          type="button"
          class="ink-button ink-button--primary"
          :disabled="targetLoading || generating || actionBusy || isModeDisabled(activeMode) || selectionTextMissing || !targetReady"
          @click="$emit('generate', activeMode)"
        >
          {{ generating ? '正在整理...' : activeModeLabel }}
        </button>
      </section>

      <p
        v-if="targetLoading || generating"
        class="ai-note"
        data-test="outline-assist-status"
        role="status"
        aria-live="polite"
      >
        {{ targetLoading ? '正在读取大纲，请稍等。' : '正在整理，请稍等。你可以继续留在这个页面。' }}
      </p>
      <p v-if="loading" class="ai-note" data-test="outline-assist-loading" role="status" aria-live="polite">
        正在刷新已有建议...
      </p>
      <p v-else-if="!suggestions.length && !generating" class="ai-note">
        还没有整理结果。点击上面的按钮开始即可。
      </p>

      <ul v-if="suggestions.length" class="ai-list outline-suggestion-list" aria-label="大纲整理结果">
        <li v-for="item in suggestions" :key="item.suggestion_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ item.title || '这次整理的结果' }}</strong>
            <span>{{ displaySuggestionType(item.suggestion_type) }}</span>
            <span v-if="item.severity">{{ displaySeverity(item.severity) }}</span>
            <span v-if="item.summary">{{ displaySummaryText(item.summary) }}</span>
          </div>

          <div
            v-if="hasOutlineComparison(item)"
            class="outline-comparison"
            :data-test="`outline-comparison-${item.suggestion_id}`"
          >
            <section class="outline-comparison-card outline-comparison-card--before">
              <h6>现在的大纲</h6>
              <p>{{ comparisonBefore(item) || '这里还没有内容。' }}</p>
            </section>
            <section class="outline-comparison-card outline-comparison-card--after">
              <h6>AI 整理后</h6>
              <p>{{ comparisonAfter(item) }}</p>
            </section>
            <div v-if="diffSummary(item).length" class="outline-change-summary">
              <strong>主要变化</strong>
              <ul>
                <li v-for="(change, index) in diffSummary(item)" :key="`${item.suggestion_id}-change-${index}`">
                  {{ displaySummaryText(change) }}
                </li>
              </ul>
            </div>
          </div>

          <section
            v-if="item.suggestion_type === 'writing_task_suggestion'"
            class="outline-writing-plan"
            :data-test="`writing-plan-${item.suggestion_id}`"
          >
            <h6>{{ suggestionPayload(item).task_title || '本章写作要点' }}</h6>
            <p v-if="suggestionPayload(item).writing_goal">
              <strong>这一章要写清：</strong>{{ suggestionPayload(item).writing_goal }}
            </p>
            <p v-if="suggestionPayload(item).must_include?.length">
              <strong>记得写到：</strong>{{ suggestionPayload(item).must_include.join('、') }}
            </p>
            <p v-if="suggestionPayload(item).must_not_include?.length">
              <strong>暂时不要写：</strong>{{ suggestionPayload(item).must_not_include.join('、') }}
            </p>
            <p v-if="suggestionPayload(item).target_word_count">
              <strong>建议字数：</strong>{{ suggestionPayload(item).target_word_count }} 字左右
            </p>
            <p class="ai-note">它只是一张写作计划，不会替你写正文；设为计划后仍需要你确认使用。</p>
          </section>

          <div v-if="suggestionDetails[item.suggestion_id]" class="ai-note">
            {{ displaySummaryText(suggestionDetails[item.suggestion_id].summary) }}
          </div>

          <p
            v-if="String(item.status || '').toLowerCase() === 'pending'"
            class="ai-note"
            :data-test="`suggestion-generating-hint-${item.suggestion_id}`"
            role="status"
            aria-live="polite"
          >
            正在整理这条建议，请稍等。
          </p>
          <div v-if="String(item.status || '').toLowerCase() === 'failed'" class="ai-actions">
            <p
              class="ai-error"
              :data-test="`suggestion-failed-hint-${item.suggestion_id}`"
            >
              这次没有整理成功。原大纲没有变化。
            </p>
            <button
              :data-test="`suggestion-retry-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--secondary"
              :disabled="targetLoading || generating || actionBusy || !targetReady || isModeDisabled(suggestionMode(item))"
              @click="$emit('generate', suggestionMode(item))"
            >
              再试一次
            </button>
          </div>
          <p
            v-if="String(item.status || '').toLowerCase() === 'accepted' && item.suggestion_type !== 'writing_task_suggestion'"
            class="ai-note"
          >
            这条建议只是先留在这里，大纲还没有变化。
          </p>
          <p
            v-if="isSelectionOnlySuggestion(item)"
            class="ai-note"
            :data-test="`suggestion-apply-hint-${item.suggestion_id}`"
          >
            这条建议只针对你选中的文字，不能直接改动整份大纲。
          </p>

          <div v-if="isStaleSuggestion(item)" class="ai-actions">
            <p class="ai-note" :data-test="`suggestion-stale-hint-${item.suggestion_id}`">
              你刚才看到的大纲已经变了，请刷新后重新整理。
            </p>
            <button
              :data-test="`suggestion-stale-refresh-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--ghost"
              :disabled="loading || targetLoading || generating || actionBusy"
              @click="$emit('refresh')"
            >
              重新读取大纲
            </button>
            <button
              :data-test="`suggestion-stale-regenerate-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--secondary"
              :disabled="loading || targetLoading || generating || actionBusy || !targetReady"
              @click="$emit('generate', suggestionMode(item))"
            >
              重新生成
            </button>
          </div>

          <div class="ai-actions">
            <button
              v-if="!hasOutlineComparison(item) && item.suggestion_type !== 'writing_task_suggestion'"
              :data-test="`suggestion-detail-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--ghost"
              :disabled="actionBusy"
              @click="$emit('suggestion-detail', item.suggestion_id)"
            >
              查看完整建议
            </button>
            <button
              v-if="canAcceptSuggestion(item)"
              :data-test="`suggestion-accept-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--secondary"
              :disabled="actionBusy"
              @click="$emit('suggestion-accept', item.suggestion_id)"
            >
              {{ isSubmitting(item, 'accept') ? '正在保留...' : '先留着' }}
            </button>
            <button
              v-if="canApplySuggestion(item)"
              :ref="(element) => setApplyTriggerRef(item.suggestion_id, element)"
              :data-test="`suggestion-apply-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--primary"
              :disabled="actionBusy"
              @click="$emit('suggestion-apply-open', item.suggestion_id)"
            >
              {{ applySubmittingSuggestionId === item.suggestion_id ? '正在写入...' : '放进大纲' }}
            </button>
            <button
              v-if="canConvertSuggestion(item)"
              :data-test="`suggestion-convert-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--primary"
              :disabled="actionBusy"
              @click="$emit('suggestion-convert', item.suggestion_id)"
            >
              {{ isSubmitting(item, 'convert') ? '正在整理计划...' : '设为本章写作计划' }}
            </button>
            <button
              v-if="isSelectionOnlySuggestion(item) && comparisonAfter(item)"
              :data-test="`suggestion-copy-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--secondary"
              :disabled="actionBusy"
              @click="$emit('suggestion-copy', item.suggestion_id)"
            >
              复制整理结果
            </button>
            <button
              v-if="canResolveSuggestion(item)"
              :data-test="`suggestion-dismiss-${item.suggestion_id}`"
              type="button"
              class="ink-button ink-button--ghost"
              :disabled="actionBusy"
              @click="$emit('suggestion-dismiss', item.suggestion_id)"
            >
              {{ isSubmitting(item, 'dismiss') ? '正在移除...' : '不要这条' }}
            </button>
          </div>

          <p
            v-if="isAcceptedWritingTaskSuggestion(item)"
            class="ai-note"
            :data-test="`suggestion-writing-task-hint-${item.suggestion_id}`"
          >
            这份计划还需要你确认使用，确认前不会进入写作流程，也不会写入正文。
          </p>

          <div
            v-if="applyConfirmSuggestionId === item.suggestion_id"
            class="outline-apply-confirm"
            :data-test="`suggestion-apply-confirm-${item.suggestion_id}`"
            role="alertdialog"
            aria-modal="false"
            :aria-labelledby="`outline-apply-title-${item.suggestion_id}`"
            :aria-describedby="`outline-apply-description-${item.suggestion_id}`"
            @keydown.esc.prevent.stop="cancelApplyConfirm"
          >
            <strong :id="`outline-apply-title-${item.suggestion_id}`">
              确定把这条建议放进{{ targetLabel }}吗？
            </strong>
            <span :id="`outline-apply-description-${item.suggestion_id}`">
              当前大纲会被修改，原内容仍可通过版本记录追溯。
            </span>
            <div class="ai-actions">
              <button
                :ref="setApplyCancelButtonRef"
                :data-test="`suggestion-apply-cancel-${item.suggestion_id}`"
                type="button"
                class="ink-button ink-button--ghost"
                :disabled="applySubmittingSuggestionId === item.suggestion_id"
                @click="$emit('suggestion-apply-cancel')"
              >
                再看看
              </button>
              <button
                :data-test="`suggestion-apply-confirm-submit-${item.suggestion_id}`"
                type="button"
                class="ink-button ink-button--primary"
                :disabled="applySubmittingSuggestionId === item.suggestion_id"
                @click="$emit('suggestion-apply-confirm-submit', item.suggestion_id)"
              >
                {{ applySubmittingSuggestionId === item.suggestion_id ? '正在写入...' : '确认放进大纲' }}
              </button>
            </div>
          </div>
        </li>
      </ul>

      <section
        v-if="pendingWritingTaskId"
        class="outline-writing-plan-confirm"
        data-test="outline-writing-plan-confirm"
      >
        <strong>这份本章写作计划还差你的确认</strong>
        <p>确认后，之后续写这一章时可以使用这些要点；现在不会生成或改动正文。</p>
        <button
          data-test="outline-writing-plan-confirm-submit"
          type="button"
          class="ink-button ink-button--primary"
          :disabled="confirmingWritingTask || actionBusy"
          @click="$emit('confirm-writing-plan')"
        >
          {{ confirmingWritingTask ? '正在确认...' : '确认使用' }}
        </button>
      </section>

      <p v-if="actionNotice" class="ai-note" role="status" aria-live="polite">{{ actionNotice }}</p>
      <p v-if="actionError" class="ai-error" role="alert">{{ actionError }}</p>

      <div v-if="conflictSectionVisible" class="ai-actions">
        <p class="ai-note">先看清冲突；处理完成后，请重新读取大纲并重新生成，不要继续使用旧建议。</p>
        <button
          data-test="outline-conflict-review"
          type="button"
          class="ink-button ink-button--secondary"
          @click="focusConflictHelp"
        >
          查看怎么处理
        </button>
      </div>
      <section
        v-if="conflictSectionVisible"
        ref="conflictHelp"
        data-test="outline-assist-conflicts"
        tabindex="-1"
        aria-labelledby="outline-conflict-heading"
      >
        <h5 id="outline-conflict-heading">需要你看一下的冲突</h5>
        <p v-if="conflictLoading" class="ai-note">正在读取冲突说明...</p>
        <p v-else-if="!conflictItems.length" class="ai-note">暂时没有可查看的冲突，请重新读取大纲后再试。</p>
        <ul v-else class="ai-list">
          <li v-for="conflict in conflictItems" :key="conflict.record_id" class="planning-item">
            <div class="candidate-summary">
              <strong>{{ conflict.title || '这份大纲有了新改动' }}</strong>
              <span>{{ displaySeverity(conflict.severity) }}</span>
              <span>{{ displayConflictSummary(conflict.summary || conflictDetails[conflict.record_id]?.summary || '请先查看差异，再重新整理。') }}</span>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const displaySummaryText = (value) => String(value || '').replace(/,/g, '，').replace(/\?/g, '？')
const displayConflictSummary = (value) => displaySummaryText(value)

const props = defineProps({
  featureEnabled: { type: Boolean, default: false },
  modes: { type: Array, default: () => [] },
  activeMode: { type: String, default: 'outline_polish' },
  targetKind: { type: String, default: 'work_outline' },
  targetLabel: { type: String, default: '作品大纲' },
  targetSelection: { type: String, default: 'work' },
  chapterOptions: { type: Array, default: () => [] },
  sourceText: { type: String, default: '' },
  suggestions: { type: Array, default: () => [] },
  suggestionDetails: { type: Object, default: () => ({}) },
  actionError: { type: String, default: '' },
  actionNotice: { type: String, default: '' },
  pendingWritingTaskId: { type: String, default: '' },
  confirmingWritingTask: { type: Boolean, default: false },
  submittingSuggestionId: { type: String, default: '' },
  submittingActionType: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  targetLoading: { type: Boolean, default: false },
  targetReady: { type: Boolean, default: true },
  generating: { type: Boolean, default: false },
  conflictSectionVisible: { type: Boolean, default: false },
  conflictLoading: { type: Boolean, default: false },
  conflictItems: { type: Array, default: () => [] },
  conflictDetails: { type: Object, default: () => ({}) },
  applyConfirmSuggestionId: { type: String, default: '' },
  applySubmittingSuggestionId: { type: String, default: '' },
  isModeDisabled: { type: Function, default: () => false },
  canAcceptSuggestion: { type: Function, required: true },
  canResolveSuggestion: { type: Function, required: true },
  canConvertSuggestion: { type: Function, required: true },
  canApplySuggestion: { type: Function, required: true },
  isAcceptedWritingTaskSuggestion: { type: Function, required: true },
  isSelectionOnlySuggestion: { type: Function, required: true },
  isStaleSuggestion: { type: Function, required: true },
  displaySuggestionType: { type: Function, required: true },
  displaySeverity: { type: Function, required: true }
})

const actionBusy = computed(() => Boolean(
  props.submittingSuggestionId || props.applySubmittingSuggestionId
))
const activeModeLabel = computed(() => (
  props.modes.find((mode) => mode.id === props.activeMode)?.label || '开始整理'
))
const activeModeHelp = computed(() => (
  props.modes.find((mode) => mode.id === props.activeMode)?.help || 'AI 只会给出建议，不会自动改动大纲。'
))
const selectionTextMissing = computed(() => (
  props.targetKind === 'selection' && !String(props.sourceText || '').trim()
))
const suggestionPayload = (item) => item?.payload ?? item?.payload_json ?? {}
const comparisonBefore = (item) => String(
  suggestionPayload(item)?.target_content_text ?? props.sourceText ?? ''
)
const comparisonAfter = (item) => String(suggestionPayload(item)?.proposed_content_text ?? '')
const hasOutlineComparison = (item) => Boolean(
  item?.suggestion_type !== 'writing_task_suggestion' && comparisonAfter(item)
)
const diffSummary = (item) => {
  const changes = suggestionPayload(item)?.diff_summary
  return Array.isArray(changes) ? changes.filter(Boolean).slice(0, 3) : []
}
const isSubmitting = (item, actionType) => (
  props.submittingSuggestionId === item?.suggestion_id && props.submittingActionType === actionType
)
const suggestionMode = (item) => ({
  chapter_outline_suggestion: 'chapter_outline_detail'
}[String(item?.suggestion_type || '')] || String(item?.suggestion_type || props.activeMode))
const chapterTargetLabel = (chapter, index) => {
  const order = Number(chapter?.order_index || index + 1)
  const title = String(chapter?.title || '').trim()
  return title ? `第${order}章 ${title}` : `第${order}章`
}

const emit = defineEmits([
  'update:active-mode',
  'update:source-text',
  'target-change',
  'generate',
  'suggestion-detail',
  'suggestion-accept',
  'suggestion-apply-open',
  'suggestion-dismiss',
  'suggestion-convert',
  'suggestion-copy',
  'confirm-writing-plan',
  'suggestion-apply-cancel',
  'suggestion-apply-confirm-submit',
  'refresh'
])

const applyCancelButton = ref(null)
const conflictHelp = ref(null)
const applyTriggerRefs = new Map()
let lastApplyTrigger = null

const setApplyTriggerRef = (suggestionId, element) => {
  const id = String(suggestionId || '')
  if (!id) return
  if (element) applyTriggerRefs.set(id, element)
  else applyTriggerRefs.delete(id)
}
const setApplyCancelButtonRef = (element) => { applyCancelButton.value = element || null }
const cancelApplyConfirm = () => {
  if (!props.applySubmittingSuggestionId) emit('suggestion-apply-cancel')
}
const focusConflictHelp = () => { conflictHelp.value?.focus() }

watch(
  () => props.applyConfirmSuggestionId,
  (nextSuggestionId, previousSuggestionId) => {
    if (nextSuggestionId) {
      const activeElement = typeof document !== 'undefined' ? document.activeElement : null
      lastApplyTrigger = applyTriggerRefs.get(String(nextSuggestionId)) || activeElement
      applyCancelButton.value?.focus()
      return
    }
    if (previousSuggestionId) {
      const trigger = lastApplyTrigger
      lastApplyTrigger = null
      if (trigger?.isConnected) trigger.focus()
    }
  },
  { flush: 'post' }
)
</script>

<style scoped>
.outline-assist-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.outline-target-label { margin: 12px 0; }
.outline-target-picker { display: grid; gap: 6px; margin-top: 12px; }
.outline-target-picker select { width: 100%; padding: 9px 10px; border: 1px solid var(--ink-border); border-radius: 10px; background: var(--ink-surface); color: inherit; font: inherit; }
.outline-source-card { display: grid; gap: 10px; margin-top: 12px; padding: 14px; border: 1px solid var(--ink-border); border-radius: 16px; background: var(--ink-surface-2); }
.outline-source-card textarea { width: 100%; box-sizing: border-box; resize: vertical; min-height: 112px; padding: 10px 12px; border: 1px solid var(--ink-border); border-radius: 10px; background: var(--ink-surface); color: inherit; font: inherit; line-height: 1.6; }
.outline-suggestion-list { margin-top: 14px; }
.outline-comparison { display: grid; gap: 10px; margin-top: 12px; }
.outline-comparison-card { padding: 12px; border: 1px solid var(--ink-border); border-radius: 12px; }
.outline-comparison-card h6, .outline-writing-plan h6 { margin: 0 0 8px; }
.outline-comparison-card p { margin: 0; white-space: pre-wrap; line-height: 1.65; }
.outline-comparison-card--before { background: var(--ink-surface-2); }
.outline-comparison-card--after { background: var(--ink-surface); border-color: var(--ink-accent); }
.outline-change-summary { padding: 0 4px; }
.outline-change-summary ul { margin: 6px 0 0; padding-left: 20px; }
.outline-writing-plan { margin-top: 12px; padding: 12px; border: 1px solid var(--ink-border); border-radius: 12px; background: var(--ink-surface-2); }
.outline-writing-plan-confirm { display: grid; gap: 8px; margin-top: 14px; padding: 14px; border: 1px solid var(--ink-accent); border-radius: 14px; background: var(--ink-surface-2); }
.outline-writing-plan-confirm p { margin: 0; }
.outline-apply-confirm { display: grid; gap: 8px; margin-top: 10px; padding: 12px; border: 1px solid var(--ink-border); border-radius: 16px; background: var(--ink-surface-2); }
</style>
