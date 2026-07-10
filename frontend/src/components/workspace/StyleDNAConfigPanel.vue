<template>
  <div v-if="featureEnabled" class="style-dna-panel" data-test="style-dna-panel">
    <div class="style-dna-panel__header">
      <div>
        <h4>风格画像</h4>
        <p>上传样章文本，提取结构化文风特征，并由你决定是否激活。</p>
      </div>
      <button
        data-test="style-dna-refresh"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="loading || extracting"
        @click="$emit('refresh')"
      >
        刷新
      </button>
    </div>

    <div class="style-dna-panel__source-mode">
      <button
        data-test="style-dna-source-user-upload"
        type="button"
        class="ink-button ink-button--ghost style-dna-panel__mode-button"
        :class="{ 'style-dna-panel__mode-button--active': sourceMode === 'user_upload' }"
        :disabled="extracting"
        @click="$emit('update:source-mode', 'user_upload')"
      >
        上传样章文本
      </button>
      <button
        data-test="style-dna-source-chapter-reference"
        type="button"
        class="ink-button ink-button--ghost style-dna-panel__mode-button"
        :class="{ 'style-dna-panel__mode-button--active': sourceMode === 'chapter_reference' }"
        :disabled="extracting"
        @click="$emit('update:source-mode', 'chapter_reference')"
      >
        从已有章节选择
      </button>
    </div>

    <div v-if="aiSettingsBlocked" class="style-dna-panel__banner style-dna-panel__banner--warning">
      <strong>AI 设置未完成</strong>
      <span>请先配置可用模型服务与任务模型，再提取风格画像。</span>
    </div>

    <div v-if="warningCopy" class="style-dna-panel__banner style-dna-panel__banner--warning">
      <strong>置信度较低</strong>
      <span>{{ warningCopy }}</span>
    </div>

    <div v-if="errorMessage" class="style-dna-panel__banner style-dna-panel__banner--error">
      <strong>处理失败</strong>
      <span>{{ errorMessage }}</span>
    </div>

    <label v-if="sourceMode === 'user_upload'" class="style-dna-panel__field">
      <span>样章文本</span>
      <textarea
        :value="draftText"
        data-test="style-dna-input"
        rows="6"
        :disabled="aiSettingsBlocked || extracting"
        placeholder="粘贴已确认章节中的样章正文，不会持久化完整文本。"
        @input="$emit('update:draft-text', $event.target.value)"
      />
    </label>

    <div v-else class="style-dna-panel__field">
      <span>从已有章节选择</span>
      <span class="style-dna-panel__hint">仅限已确认章节，最多选择 3 章；草稿章节不可作为样章来源。</span>
      <div v-if="chapterOptions.length" class="style-dna-panel__chapter-options">
        <label
          v-for="option in chapterOptions"
          :key="option.id"
          class="style-dna-panel__chapter-option"
        >
          <input
            :data-test="`style-dna-chapter-option-${option.id}`"
            type="checkbox"
            :checked="selectedChapterIds.includes(option.id)"
            :disabled="option.disabled || (selectedChapterIds.length >= 3 && !selectedChapterIds.includes(option.id))"
            @change="toggleChapterSelection(option.id, $event.target.checked)"
          />
          <span>{{ option.label }}</span>
        </label>
      </div>
      <span v-else class="style-dna-panel__hint">暂无可用的已确认章节。</span>
    </div>

    <div class="style-dna-panel__meta">
      <span>字数 {{ characterCount }}</span>
      <span v-if="extractJobActive">提取中，请稍候</span>
      <span v-else-if="currentStatus">状态 {{ currentStatus }}</span>
      <span v-if="currentProfile?.confidence !== undefined">置信度 {{ confidenceLabel }}</span>
    </div>

    <div class="style-dna-panel__actions">
      <button
        data-test="style-dna-extract"
        type="button"
        class="ink-button ink-button--primary"
        :disabled="aiSettingsBlocked || extracting || !canExtract"
        @click="$emit('extract')"
      >
        {{ extractJobActive ? '提取中…' : '开始提取' }}
      </button>
      <button
        v-if="currentProfile?.status === 'pending_confirm'"
        data-test="style-dna-confirm"
        type="button"
        class="ink-button ink-button--secondary"
        :disabled="extracting"
        @click="$emit('confirm-profile', currentProfile.profile_id)"
      >
        激活画像
      </button>
      <button
        v-if="activeProfile?.status === 'active'"
        data-test="style-dna-disable"
        type="button"
        class="ink-button ink-button--ghost"
        :disabled="extracting"
        @click="$emit('disable-profile', activeProfile.profile_id)"
      >
        关闭
      </button>
      <button
        v-if="currentProfile?.status === 'pending_confirm'"
        data-test="style-dna-delete-pending"
        type="button"
        class="ink-button ink-button--danger"
        :disabled="extracting"
        @click="$emit('delete-profile', currentProfile.profile_id)"
      >
        删除待确认
      </button>
    </div>

    <div v-if="currentProfile" class="style-dna-panel__card">
      <div class="style-dna-panel__card-header">
        <strong>当前查看</strong>
        <span>{{ currentProfile.profile_id }}</span>
        <span class="style-dna-panel__status-pill">{{ statusLabel(currentProfile.status) }}</span>
      </div>
      <p class="style-dna-panel__summary">{{ currentProfile.style_summary || '-' }}</p>
      <div v-if="currentProfile.style_tags?.length" class="style-dna-panel__tags">
        <span v-for="tag in currentProfile.style_tags" :key="tag" class="style-dna-panel__tag">{{ tag }}</span>
      </div>
      <div class="style-dna-panel__metrics">
        <span>对白占比 {{ ratioLabel(currentProfile.dialogue_ratio) }}</span>
        <span>平均句长 {{ lengthLabel(currentProfile.avg_sentence_length) }}</span>
        <span>心理描写占比 {{ ratioLabel(currentProfile.psychological_ratio) }}</span>
        <span>动作描写占比 {{ ratioLabel(currentProfile.action_ratio) }}</span>
        <span>环境描写占比 {{ ratioLabel(currentProfile.description_ratio) }}</span>
        <span>叙述视角 {{ perspectiveLabel(currentProfile.narrative_perspective) }}</span>
        <span>时态偏好 {{ tenseLabel(currentProfile.tense_preference) }}</span>
      </div>
      <p v-if="currentProfile.low_confidence_reason" class="style-dna-panel__note">
        低置信度原因：{{ currentProfile.low_confidence_reason }}
      </p>
    </div>

    <div v-else-if="activeProfile" class="style-dna-panel__card">
      <div class="style-dna-panel__card-header">
        <strong>当前激活</strong>
        <span>{{ activeProfile.profile_id }}</span>
        <span class="style-dna-panel__status-pill">{{ statusLabel(activeProfile.status) }}</span>
      </div>
      <p class="style-dna-panel__summary">{{ activeProfile.style_summary || '-' }}</p>
      <div class="style-dna-panel__metrics">
        <span>对白占比 {{ ratioLabel(activeProfile.dialogue_ratio) }}</span>
        <span>平均句长 {{ lengthLabel(activeProfile.avg_sentence_length) }}</span>
        <span>心理描写占比 {{ ratioLabel(activeProfile.psychological_ratio) }}</span>
        <span>动作描写占比 {{ ratioLabel(activeProfile.action_ratio) }}</span>
        <span>环境描写占比 {{ ratioLabel(activeProfile.description_ratio) }}</span>
        <span>叙述视角 {{ perspectiveLabel(activeProfile.narrative_perspective) }}</span>
        <span>时态偏好 {{ tenseLabel(activeProfile.tense_preference) }}</span>
      </div>
      <p v-if="activeProfile.low_confidence_reason" class="style-dna-panel__note">
        低置信度原因：{{ activeProfile.low_confidence_reason }}
      </p>
    </div>

    <div v-if="historyProfiles.length" class="style-dna-panel__history">
      <strong>历史版本</strong>
      <ul>
        <li v-for="profile in historyProfiles" :key="profile.profile_id">
          <button
            :data-test="`style-dna-history-${profile.profile_id}`"
            type="button"
            :class="historyItemClass(profile)"
            @click="$emit('view-profile', profile.profile_id)"
          >
            <span>{{ profile.profile_id }}</span>
            <span>v{{ profile.version || 1 }}</span>
            <span>{{ statusLabel(profile.status) }}</span>
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
  extracting: {
    type: Boolean,
    default: false
  },
  extractJobActive: {
    type: Boolean,
    default: false
  },
  draftText: {
    type: String,
    default: ''
  },
  sourceMode: {
    type: String,
    default: 'user_upload'
  },
  chapterOptions: {
    type: Array,
    default: () => []
  },
  selectedChapterIds: {
    type: Array,
    default: () => []
  },
  activeProfile: {
    type: Object,
    default: null
  },
  currentProfile: {
    type: Object,
    default: null
  },
  historyProfiles: {
    type: Array,
    default: () => []
  },
  warningMessage: {
    type: String,
    default: ''
  },
  errorMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'update:draft-text',
  'update:source-mode',
  'update:selected-chapter-ids',
  'extract',
  'confirm-profile',
  'disable-profile',
  'delete-profile',
  'view-profile',
  'refresh'
])

const characterCount = computed(() => String(props.draftText || '').trim().length)
const canExtract = computed(() => (
  props.sourceMode === 'chapter_reference'
    ? props.selectedChapterIds.length > 0
    : characterCount.value > 0
))
const currentStatus = computed(() => String(props.currentProfile?.status || props.activeProfile?.status || ''))
const confidenceLabel = computed(() => {
  const value = Number(props.currentProfile?.confidence ?? props.activeProfile?.confidence ?? 0)
  if (!Number.isFinite(value) || value <= 0) return '-'
  return `${Math.round(value * 100)}%`
})
const warningCopy = computed(() => {
  if (props.warningMessage) return props.warningMessage
  if (props.currentProfile?.low_confidence_reason) {
    return `当前画像置信度较低：${props.currentProfile.low_confidence_reason}`
  }
  if (props.activeProfile?.low_confidence_reason) {
    return `当前画像置信度较低：${props.activeProfile.low_confidence_reason}`
  }
  return ''
})

const ratioLabel = (value) => {
  const ratio = Number(value ?? 0)
  if (!Number.isFinite(ratio) || ratio < 0) return '-'
  return `${Math.round(ratio * 100)}%`
}

const lengthLabel = (value) => {
  const length = Number(value ?? 0)
  if (!Number.isFinite(length) || length <= 0) return '-'
  return `${Math.round(length)} 字`
}

const perspectiveLabel = (value) => ({
  first_person: '第一人称',
  third_person_limited: '第三人称限知',
  omniscient: '全知视角'
}[String(value || '')] || '-')

const tenseLabel = (value) => ({
  past: '过去时',
  present: '现在时',
  mixed: '混合'
}[String(value || '')] || '-')

const statusLabel = (value) => ({
  pending_confirm: '待确认',
  active: '已激活',
  disabled: '已关闭',
  archived: '已归档'
}[String(value || '')] || String(value || '-'))

const historyItemClass = (profile) => ({
  'style-dna-panel__history-item': true,
  'style-dna-panel__history-item--current': String(profile?.profile_id || '') === String(props.currentProfile?.profile_id || ''),
  'style-dna-panel__history-item--active': String(profile?.profile_id || '') === String(props.activeProfile?.profile_id || '')
})

const toggleChapterSelection = (chapterId, checked) => {
  const nextIds = new Set(props.selectedChapterIds.map((item) => String(item || '')))
  if (checked) {
    if (nextIds.size >= 3 && !nextIds.has(String(chapterId || ''))) return
    nextIds.add(String(chapterId || ''))
  } else {
    nextIds.delete(String(chapterId || ''))
  }
  emit('update:selected-chapter-ids', Array.from(nextIds))
}
</script>

<style scoped>
.style-dna-panel {
  display: grid;
  gap: 12px;
}

.style-dna-panel__header,
.style-dna-panel__card-header,
.style-dna-panel__meta,
.style-dna-panel__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.style-dna-panel__header h4,
.style-dna-panel__history strong {
  margin: 0;
  color: var(--ai-title, #111827);
}

.style-dna-panel__header p,
.style-dna-panel__summary,
.style-dna-panel__note {
  margin: 4px 0 0;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.style-dna-panel__field {
  display: grid;
  gap: 8px;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.style-dna-panel__source-mode {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.style-dna-panel__mode-button--active {
  background: var(--ai-bg-soft, #f1f5f9);
  font-weight: 600;
}

.style-dna-panel__hint {
  color: var(--ai-text-muted, #6b7280);
  font-size: 12px;
}

.style-dna-panel__chapter-options {
  display: grid;
  gap: 8px;
}

.style-dna-panel__chapter-option {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.style-dna-panel__field textarea {
  width: 100%;
  min-height: 120px;
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 12px;
  padding: 10px 12px;
  resize: vertical;
  font: inherit;
  color: var(--ai-title, #111827);
  background: var(--ai-bg, #ffffff);
}

.style-dna-panel__banner,
.style-dna-panel__card,
.style-dna-panel__history {
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 14px;
  padding: 12px;
  background: var(--ai-bg-soft, #f8fafc);
}

.style-dna-panel__banner {
  display: grid;
  gap: 4px;
}

.style-dna-panel__banner--warning {
  background: color-mix(in srgb, var(--ai-warning-bg, #fff7ed) 85%, var(--ai-bg, #ffffff));
}

.style-dna-panel__banner--error {
  background: color-mix(in srgb, var(--ai-danger-bg, #fef2f2) 85%, var(--ai-bg, #ffffff));
}

.style-dna-panel__tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.style-dna-panel__tag {
  border: 1px solid var(--ai-border, #d1d5db);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--ai-text, #4b5563);
  background: var(--ai-bg, #ffffff);
}

.style-dna-panel__metrics {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--ai-text, #4b5563);
  font-size: 12px;
}

.style-dna-panel__status-pill {
  border-radius: 999px;
  padding: 2px 8px;
  background: var(--ai-bg, #ffffff);
  border: 1px solid var(--ai-border, #d1d5db);
  font-size: 12px;
  color: var(--ai-text, #4b5563);
}

.style-dna-panel__history ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--ai-text, #4b5563);
  font-size: 13px;
}

.style-dna-panel__history li {
  margin-bottom: 6px;
}

.style-dna-panel__history-item {
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

.style-dna-panel__history-item--current {
  border-color: var(--ai-accent, #3b82f6);
  background: color-mix(in srgb, var(--ai-accent-soft, #dbeafe) 40%, var(--ai-bg, #ffffff));
}

.style-dna-panel__history-item--active {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ai-success, #10b981) 50%, transparent);
}
</style>
