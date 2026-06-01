﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="status-bar">
    <div v-if="offline" class="offline-banner">{{ offlineMessage }}</div>

    <div class="status-main">
      <div class="status-pill" :data-status="status">
        <span class="status-icon" :class="{ spinning: isSaving }" />
        <span>{{ statusLabel }}</span>
      </div>

      <div class="status-meta">
        <span>本章字数 {{ formattedWordCount }}</span>
        <span>今日新增 {{ formattedTodayWordDelta }}</span>
        <span>会话{{ sessionReady ? '已加载' : '未加载' }}</span>
        <span v-if="lastSyncedAt">最近同步 {{ lastSyncedAt }}</span>
        <span v-if="statusDetail">{{ statusDetail }}</span>
        <span v-if="retryCount > 0">重试次数 {{ retryCount }}</span>
        <span v-if="formattedNextRetryAt">下次重试 {{ formattedNextRetryAt }}</span>
        <button
          v-if="showManualRetry"
          type="button"
          class="retry-button"
          @click="$emit('manual-retry')"
        >
          手动重试
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'synced'
  },
  wordCount: {
    type: Number,
    default: 0
  },
  todayWordDelta: {
    type: Number,
    default: 0
  },
  sessionReady: {
    type: Boolean,
    default: false
  },
  offline: {
    type: Boolean,
    default: false
  },
  offlineMessage: {
    type: String,
    default: '离线模式：当前网络离线，已开启本地缓存保护。'
  },
  lastSyncedAt: {
    type: String,
    default: ''
  },
  statusDetail: {
    type: String,
    default: ''
  },
  retryCount: {
    type: Number,
    default: 0
  },
  nextRetryAt: {
    type: String,
    default: ''
  },
  showManualRetry: {
    type: Boolean,
    default: false
  }
})

defineEmits(['manual-retry'])

const statusLabelMap = {
  synced: '已保存',
  saving: '保存中',
  offline: '离线模式',
  conflict: '检测到冲突',
  error: '保存失败'
}

const status = computed(() => String(props.status || 'synced'))
const isSaving = computed(() => status.value === 'saving')
const statusLabel = computed(() => statusLabelMap[status.value] || statusLabelMap.synced)
const formattedWordCount = computed(() => Number(props.wordCount || 0).toLocaleString('zh-CN'))
const formattedTodayWordDelta = computed(() => Math.max(0, Number(props.todayWordDelta || 0)).toLocaleString('zh-CN'))
const formattedNextRetryAt = computed(() => {
  if (!props.nextRetryAt) return ''
  const next = new Date(props.nextRetryAt)
  if (Number.isNaN(next.getTime())) return String(props.nextRetryAt)
  return next.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
})
</script>

<style scoped>
.status-bar {
  --status-border: var(--studio-border, var(--ink-border, #e5e7eb));
  --status-text: var(--studio-text, var(--ink-text-secondary, #6b7280));

  display: grid;
  gap: 8px;
  min-width: 280px;
}

.offline-banner {
  border: 1px solid var(--ink-warning-text, #fcd34d);
  border-radius: 999px;
  background: var(--ink-warning-bg, #fef3c7);
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-warning-text, #92400e);
}

.status-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--ink-success-text, #15803d) 30%, transparent);
  border-radius: 999px;
  background: var(--ink-success-bg, #f0fdf4);
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-success-text, #15803d);
  white-space: nowrap;
}

.status-pill[data-status='saving'] {
  border-color: var(--ink-accent-soft, #dbeafe);
  background: color-mix(in srgb, var(--ink-accent-soft, #eff6ff) 72%, var(--studio-card-bg, #fff));
  color: var(--ink-accent, #1d4ed8);
}

.status-pill[data-status='error'] {
  border-color: color-mix(in srgb, var(--ink-warning-text, #c2410c) 35%, transparent);
  background: var(--ink-warning-bg, #fff7ed);
  color: var(--ink-warning-text, #c2410c);
}

.status-pill[data-status='conflict'] {
  border-color: color-mix(in srgb, var(--ink-danger-text, #be185d) 30%, transparent);
  background: var(--ink-danger-bg, #fdf2f8);
  color: var(--ink-danger-text, #be185d);
}

.status-pill[data-status='offline'] {
  border-color: color-mix(in srgb, var(--ink-warning-text, #b45309) 30%, transparent);
  background: var(--ink-warning-bg, #fffbeb);
  color: var(--ink-warning-text, #b45309);
}

.status-icon {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: currentColor;
  flex: 0 0 auto;
}

.status-icon.spinning {
  border: 2px solid currentColor;
  border-right-color: transparent;
  background: transparent;
  animation: spin 0.8s linear infinite;
}

.status-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: var(--status-text);
}

.retry-button {
  border: 1px solid color-mix(in srgb, var(--ink-warning-text, #c2410c) 35%, transparent);
  border-radius: 999px;
  background: var(--ink-warning-bg, #fff7ed);
  color: var(--ink-warning-text, #c2410c);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 760px) {
  .status-main {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
