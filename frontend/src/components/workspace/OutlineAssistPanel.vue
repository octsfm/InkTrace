<template>
  <div v-if="featureEnabled" class="outline-assist-panel" data-test="outline-assist-panel">
    <div class="ai-helper-view" data-test="outline-assist-view">
      <div class="outline-assist-header">
        <h5>大纲辅助</h5>
        <button
          data-test="outline-assist-refresh"
          type="button"
          :disabled="loading"
          @click="$emit('refresh')"
        >
          {{ loading ? '刷新中...' : '刷新建议' }}
        </button>
      </div>
      <div class="ai-helper-nav" data-test="outline-assist-mode-nav">
        <button
          v-for="mode in modes"
          :key="mode.id"
          :data-test="`outline-assist-mode-${mode.id}`"
          type="button"
          class="ai-helper-tab"
          :class="{ 'ai-helper-tab--active': activeMode === mode.id }"
          @click="$emit('update:active-mode', mode.id)"
        >
          {{ mode.label }}
        </button>
      </div>
      <p v-if="loading" class="ai-note" data-test="outline-assist-loading">正在加载建议…</p>
      <p v-else-if="!suggestions.length" class="ai-note">当前模式下暂无建议，生成后会在这里展示。</p>
      <ul v-else class="ai-list">
        <li v-for="item in suggestions" :key="item.suggestion_id" class="planning-item">
          <div class="candidate-summary">
            <strong>{{ item.title }}</strong>
            <span>{{ displaySuggestionType(item.suggestion_type) }}</span>
            <span>{{ displaySeverity(item.severity) }}</span>
            <span>{{ item.summary }}</span>
          </div>
          <div class="ai-actions">
            <button
              :data-test="`suggestion-detail-${item.suggestion_id}`"
              type="button"
              @click="$emit('suggestion-detail', item.suggestion_id)"
            >
              查看建议
            </button>
            <button
              v-if="canAcceptSuggestion(item)"
              :data-test="`suggestion-accept-${item.suggestion_id}`"
              type="button"
              :disabled="submittingSuggestionId === item.suggestion_id"
              @click="$emit('suggestion-accept', item.suggestion_id)"
            >
              {{ submittingSuggestionId === item.suggestion_id && submittingActionType === 'accept' ? '采纳中...' : '采纳建议' }}
            </button>
            <button
              v-if="canApplySuggestion(item)"
              :data-test="`suggestion-apply-${item.suggestion_id}`"
              type="button"
              :disabled="applySubmittingSuggestionId === item.suggestion_id"
              @click="$emit('suggestion-apply-open', item.suggestion_id)"
            >
              {{ applySubmittingSuggestionId === item.suggestion_id ? '应用中...' : '应用到大纲' }}
            </button>
            <button
              v-if="canResolveSuggestion(item)"
              :data-test="`suggestion-dismiss-${item.suggestion_id}`"
              type="button"
              :disabled="submittingSuggestionId === item.suggestion_id"
              @click="$emit('suggestion-dismiss', item.suggestion_id)"
            >
              {{ submittingSuggestionId === item.suggestion_id && submittingActionType === 'dismiss' ? '忽略中...' : '忽略建议' }}
            </button>
            <button
              v-if="canConvertSuggestion(item)"
              :data-test="`suggestion-convert-${item.suggestion_id}`"
              type="button"
              :disabled="submittingSuggestionId === item.suggestion_id"
              @click="$emit('suggestion-convert', item.suggestion_id)"
            >
              {{ submittingSuggestionId === item.suggestion_id && submittingActionType === 'convert' ? '转换中...' : '转为执行动作' }}
            </button>
          </div>
          <p
            v-if="isAcceptedWritingTaskSuggestion(item)"
            class="ai-note"
            :data-test="`suggestion-writing-task-hint-${item.suggestion_id}`"
          >
            已进入写作任务确认链，待二次确认后才会进入 Writer 可消费状态。
          </p>
          <p
            v-if="String(item.status || '').toLowerCase() === 'generating'"
            class="ai-note"
            :data-test="`suggestion-generating-hint-${item.suggestion_id}`"
          >
            建议生成中，请稍后刷新查看结果。
          </p>
          <p
            v-if="String(item.status || '').toLowerCase() === 'failed'"
            class="ai-error"
            :data-test="`suggestion-failed-hint-${item.suggestion_id}`"
          >
            建议生成失败，请稍后重试。
          </p>
          <p
            v-if="isSelectionOnlySuggestion(item)"
            class="ai-note"
            :data-test="`suggestion-apply-hint-${item.suggestion_id}`"
          >
            当前建议针对自由文本片段，需先选择目标大纲节点后才能应用。
          </p>
          <div
            v-if="isStaleSuggestion(item)"
            class="ai-actions"
          >
            <p
              class="ai-note"
              :data-test="`suggestion-stale-hint-${item.suggestion_id}`"
            >
              大纲已被修改，建议可能已不适用。
            </p>
            <button
              :data-test="`suggestion-stale-refresh-${item.suggestion_id}`"
              type="button"
              :disabled="loading"
              @click="$emit('refresh')"
            >
              {{ loading ? '刷新中...' : '刷新建议' }}
            </button>
          </div>
          <div
            v-if="applyConfirmSuggestionId === item.suggestion_id"
            class="outline-apply-confirm"
            :data-test="`suggestion-apply-confirm-${item.suggestion_id}`"
          >
            <strong>确定要将 1 条建议应用到大纲吗？</strong>
            <span>这将会修改正式大纲内容。</span>
            <div class="ai-actions">
              <button
                :data-test="`suggestion-apply-cancel-${item.suggestion_id}`"
                type="button"
                :disabled="applySubmittingSuggestionId === item.suggestion_id"
                @click="$emit('suggestion-apply-cancel')"
              >
                取消
              </button>
              <button
                :data-test="`suggestion-apply-confirm-submit-${item.suggestion_id}`"
                type="button"
                :disabled="applySubmittingSuggestionId === item.suggestion_id"
                @click="$emit('suggestion-apply-confirm-submit', item.suggestion_id)"
              >
                {{ applySubmittingSuggestionId === item.suggestion_id ? '应用中...' : '确认应用' }}
              </button>
            </div>
          </div>
          <div v-if="suggestionDetails[item.suggestion_id]" class="ai-note">
            {{ suggestionDetails[item.suggestion_id].summary }}
          </div>
        </li>
      </ul>
      <p v-if="actionError" class="ai-error">{{ actionError }}</p>
      <div v-if="conflictSectionVisible" data-test="outline-assist-conflicts">
        <h5>大纲辅助冲突详情</h5>
        <p v-if="conflictLoading" class="ai-note">正在加载冲突详情…</p>
        <p v-else-if="!conflictItems.length" class="ai-note">当前没有可展示的冲突，请刷新后重试。</p>
        <ul v-else class="ai-list">
          <li
            v-for="conflict in conflictItems"
            :key="conflict.record_id"
            class="planning-item"
          >
            <div class="candidate-summary">
              <strong>{{ conflict.title || '待处理冲突' }}</strong>
              <span>{{ displaySeverity(conflict.severity) }}</span>
              <span>{{ conflict.summary || conflictDetails[conflict.record_id]?.summary || '请先确认差异后再继续处理。' }}</span>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  featureEnabled: {
    type: Boolean,
    default: false
  },
  modes: {
    type: Array,
    default: () => []
  },
  activeMode: {
    type: String,
    default: 'outline_polish'
  },
  suggestions: {
    type: Array,
    default: () => []
  },
  suggestionDetails: {
    type: Object,
    default: () => ({})
  },
  actionError: {
    type: String,
    default: ''
  },
  submittingSuggestionId: {
    type: String,
    default: ''
  },
  submittingActionType: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  conflictSectionVisible: {
    type: Boolean,
    default: false
  },
  conflictLoading: {
    type: Boolean,
    default: false
  },
  conflictItems: {
    type: Array,
    default: () => []
  },
  conflictDetails: {
    type: Object,
    default: () => ({})
  },
  applyConfirmSuggestionId: {
    type: String,
    default: ''
  },
  applySubmittingSuggestionId: {
    type: String,
    default: ''
  },
  canApplySuggestion: {
    type: Function,
    default: () => false
  },
  canAcceptSuggestion: {
    type: Function,
    default: () => false
  },
  canResolveSuggestion: {
    type: Function,
    default: () => false
  },
  canConvertSuggestion: {
    type: Function,
    default: () => false
  },
  isAcceptedWritingTaskSuggestion: {
    type: Function,
    default: () => false
  },
  isSelectionOnlySuggestion: {
    type: Function,
    default: () => false
  },
  isStaleSuggestion: {
    type: Function,
    default: () => false
  },
  displaySuggestionType: {
    type: Function,
    default: (value) => String(value || '-')
  },
  displaySeverity: {
    type: Function,
    default: (value) => String(value || '-')
  }
})

defineEmits([
  'update:active-mode',
  'suggestion-detail',
  'suggestion-accept',
  'suggestion-apply-open',
  'suggestion-dismiss',
  'suggestion-convert',
  'suggestion-apply-cancel',
  'suggestion-apply-confirm-submit',
  'refresh'
])
</script>
