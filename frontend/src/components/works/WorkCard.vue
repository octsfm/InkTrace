<template>
  <article class="work-card-shell" @click="$emit('open', work.id)">
    <div class="work-card-top">
      <div class="work-cover">{{ coverText }}</div>
      <div class="work-main">
        <h3 class="work-title">{{ work.title }}</h3>
        <p class="work-meta">作者：{{ work.author || '未填写' }}</p>
      </div>
    </div>
    <div class="work-stats">
      <div class="stat-chip">
        <span class="stat-chip-label">字数</span>
        <span class="stat-chip-value">{{ formatNumber(work.current_word_count) }}</span>
      </div>
      <div class="stat-chip">
        <span class="stat-chip-label">更新</span>
        <span class="stat-chip-value">{{ formatDate(work.updated_at) }}</span>
      </div>
    </div>
    <div class="work-footer">
      <span class="work-enter">进入写作页</span>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  work: {
    type: Object,
    required: true
  }
})

defineEmits(['open'])

const coverText = computed(() => String(props.work?.title || '作品').slice(0, 2))

const formatNumber = (num) => Number(num || 0).toLocaleString('zh-CN')

const formatDate = (value) => {
  if (!value) return '刚刚创建'
  try {
    return new Date(value).toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric'
    })
  } catch (error) {
    return '刚刚创建'
  }
}
</script>

<style scoped>
.work-card-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 22px;
  background-color: #ffffff;
  cursor: pointer;
  transition: all 0.22s ease;
}

.work-card-shell:hover {
  transform: translateY(-2px);
  border-color: #d1d5db;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.work-card-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.work-cover {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(180deg, #111827 0%, #374151 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}

.work-main {
  min-width: 0;
}

.work-title {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  line-height: 1.35;
}

.work-meta {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
}

.work-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat-chip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: 14px;
  background-color: #f9fafb;
}

.stat-chip-label {
  font-size: 12px;
  color: #9ca3af;
}

.stat-chip-value {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.work-footer {
  display: flex;
  justify-content: flex-end;
}

.work-enter {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
}

@media (max-width: 760px) {
  .work-stats {
    grid-template-columns: 1fr;
  }
}
</style>
