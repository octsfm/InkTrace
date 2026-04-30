<template>
  <article class="work-card-shell" @click="$emit('open', work.id)">
    <div class="work-card-actions">
      <button type="button" class="more-button" @click.stop="toggleMenu">...</button>
      <div v-if="menuVisible" class="card-menu" @click.stop>
        <button type="button" class="menu-item rename" @click.stop="emitAction('rename')">重命名</button>
        <button type="button" class="menu-item author" @click.stop="emitAction('change-author')">修改作者</button>
        <button type="button" class="menu-item export" @click.stop="emitAction('export')">导出 TXT</button>
        <button type="button" class="menu-item danger" @click.stop="openDeleteConfirm">删除作品</button>
      </div>
    </div>

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
        <span class="stat-chip-value">{{ formatNumber(work.word_count ?? work.current_word_count) }}</span>
      </div>
      <div class="stat-chip">
        <span class="stat-chip-label">更新</span>
        <span class="stat-chip-value">{{ formatDate(work.updated_at) }}</span>
      </div>
    </div>

    <div class="work-footer">
      <span class="work-enter">进入写作页</span>
    </div>

    <div v-if="confirmVisible" class="confirm-mask" @click.stop>
      <div class="confirm-panel">
        <h4>确认删除作品？</h4>
        <p>此操作不可恢复，确认删除？</p>
        <div class="confirm-actions">
          <button type="button" class="ghost-button" @click.stop="closeDeleteConfirm">取消</button>
          <button type="button" class="danger-button" :disabled="deleting" @click.stop="confirmDelete">
            {{ deleting ? '删除中...' : '删除' }}
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  work: {
    type: Object,
    required: true
  },
  deleting: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['open', 'delete', 'rename', 'change-author', 'export'])

const menuVisible = ref(false)
const confirmVisible = ref(false)

const coverText = computed(() => String(props.work?.title || '作品').slice(0, 2))

const toggleMenu = () => {
  menuVisible.value = !menuVisible.value
}

const openDeleteConfirm = () => {
  menuVisible.value = false
  confirmVisible.value = true
}

const emitAction = (eventName) => {
  menuVisible.value = false
  emit(eventName, props.work)
}

const closeDeleteConfirm = () => {
  if (props.deleting) return
  confirmVisible.value = false
}

const confirmDelete = () => {
  if (props.deleting) return
  emit('delete', props.work.id)
}

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
  position: relative;
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

.work-card-actions {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
}

.more-button {
  width: 34px;
  height: 34px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #ffffff;
  color: #4b5563;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.card-menu {
  position: absolute;
  top: 40px;
  right: 0;
  min-width: 132px;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
}

.menu-item {
  width: 100%;
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  background: transparent;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}

.menu-item:hover {
  background: #f9fafb;
}

.menu-item.danger {
  color: #b91c1c;
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

.confirm-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  border-radius: 22px;
  background: rgba(15, 23, 42, 0.18);
}

.confirm-panel {
  width: 100%;
  max-width: 280px;
  border-radius: 18px;
  background: #ffffff;
  padding: 18px;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
}

.confirm-panel h4 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.confirm-panel p {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #6b7280;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.ghost-button,
.danger-button {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #ffffff;
  color: #374151;
}

.danger-button {
  border-color: #dc2626;
  background: #dc2626;
  color: #ffffff;
}

.danger-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

@media (max-width: 760px) {
  .work-stats {
    grid-template-columns: 1fr;
  }
}
</style>
