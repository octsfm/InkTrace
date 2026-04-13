<template>
  <header class="workspace-top-bar">
    <div class="topbar-main">
      <div class="breadcrumb-row">
        <span class="crumb">我的小说</span>
        <span class="separator">/</span>
        <span class="crumb">{{ novelTitle }}</span>
        <template v-if="objectLabel">
          <span class="separator">/</span>
          <span class="crumb current">{{ objectLabel }}</span>
        </template>
      </div>

      <div class="title-row">
        <h1>{{ viewTitle }}</h1>
        <p>{{ viewDescription }}</p>
      </div>

      <div class="pulse-row">
        <div class="pulse-chip">
          <span class="pulse-label">保存</span>
          <span class="pulse-value">{{ saveStatusText }}</span>
        </div>
        <div class="pulse-chip">
          <span class="pulse-label">任务</span>
          <span class="pulse-value">{{ taskStatusText }}</span>
        </div>
        <div class="pulse-chip">
          <span class="pulse-label">字数</span>
          <span class="pulse-value">{{ wordCount }}</span>
        </div>
      </div>

      <div v-if="props.quickFacts.length" class="facts-row">
        <div v-for="item in props.quickFacts" :key="item.label" class="fact-chip">
          <span class="fact-label">{{ item.label }}</span>
          <span class="fact-value">{{ item.value }}</span>
        </div>
      </div>
    </div>

    <div class="topbar-side">
      <div class="status-grid">
        <div
          v-for="item in props.statusCards"
          :key="item.label"
          class="meta-pill"
          :class="item.tone ? `tone-${item.tone}` : ''"
        >
          <span class="pill-label">{{ item.label }}</span>
          <span class="pill-value">{{ item.value }}</span>
          <span v-if="item.hint" class="pill-hint">{{ item.hint }}</span>
        </div>
      </div>

      <div class="action-row">
        <button type="button" class="soft-button" @click="$emit('open-command-palette')">
          <span>命令面板</span>
          <span class="button-shortcut">Ctrl+K</span>
        </button>
        <button
          v-for="item in props.objectActions"
          :key="item.label"
          type="button"
          class="soft-button"
          @click="$emit('action', item.action)"
        >
          {{ item.label }}
        </button>
        <button type="button" class="ghost-button" @click="$emit('toggle-copilot')">
          {{ copilotOpen ? '收起助手' : '打开助手' }}
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
const props = defineProps({
  novelTitle: {
    type: String,
    default: '未命名小说'
  },
  objectLabel: {
    type: String,
    default: ''
  },
  viewTitle: {
    type: String,
    default: '写作工作区'
  },
  viewDescription: {
    type: String,
    default: ''
  },
  saveStatusText: {
    type: String,
    default: '待命中'
  },
  taskStatusText: {
    type: String,
    default: '暂无任务'
  },
  wordCount: {
    type: [String, Number],
    default: 0
  },
  quickFacts: {
    type: Array,
    default: () => []
  },
  statusCards: {
    type: Array,
    default: () => []
  },
  objectActions: {
    type: Array,
    default: () => []
  },
  copilotOpen: {
    type: Boolean,
    default: true
  }
})

defineEmits(['toggle-copilot', 'action', 'open-command-palette'])
</script>

<style scoped>
.workspace-top-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 24px 16px;
  border-bottom: 1px solid #E5E7EB;
  background-color: #ffffff;
}

.topbar-main {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.breadcrumb-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 12px;
  color: #6B7280;
}

.crumb {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crumb.current {
  color: #111827;
  font-weight: 600;
}

.separator {
  color: #D1D5DB;
}

.title-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-row h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.title-row p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #6B7280;
}

.facts-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pulse-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pulse-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background: linear-gradient(180deg, #FFFFFF 0%, #F9FAFB 100%);
}

.pulse-label {
  font-size: 11px;
  color: #9CA3AF;
}

.pulse-value {
  font-size: 12px;
  font-weight: 600;
  color: #111827;
}

.fact-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
}

.fact-label {
  font-size: 11px;
  color: #9CA3AF;
}

.fact-value {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.topbar-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
  justify-content: flex-end;
  min-width: 360px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(92px, 1fr));
  gap: 12px;
}

.meta-pill {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 92px;
  padding: 10px 12px;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  background-color: #FFFFFF;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.03);
}

.pill-label {
  font-size: 11px;
  color: #9CA3AF;
}

.pill-value {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.pill-hint {
  font-size: 11px;
  color: #9CA3AF;
}

.tone-primary {
  background-color: #F8FAFF;
  border-color: #DBEAFE;
}

.tone-warning {
  background-color: #FFFBEB;
  border-color: #FDE68A;
}

.tone-success {
  background-color: #F0FDF4;
  border-color: #BBF7D0;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.soft-button,
.ghost-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  background-color: #ffffff;
  color: #374151;
  font-size: 13px;
  font-weight: 500;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.soft-button {
  background-color: #F9FAFB;
}

.soft-button:hover,
.ghost-button:hover {
  background-color: #F9FAFB;
  border-color: #D1D5DB;
}

.button-shortcut {
  font-size: 11px;
  color: #9CA3AF;
}

@media (max-width: 1200px) {
  .workspace-top-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-side {
    min-width: 0;
  }

  .action-row {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
