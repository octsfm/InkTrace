<template>
  <el-card shadow="never" class="chapter-task-card">
    <template #header>
      <div>
        <div class="eyebrow">Task</div>
        <span class="panel-title">{{ title }}</span>
      </div>
    </template>
    <div v-if="!hasTask" class="empty-text">暂无任务摘要</div>
    <el-descriptions v-else :column="1" border size="small">
      <el-descriptions-item label="章节功能">{{ formatChapterFunction(task.chapter_function) }}</el-descriptions-item>
      <el-descriptions-item label="本章目标">{{ joinList(task.goals) }}</el-descriptions-item>
      <el-descriptions-item label="必承接点">{{ joinList(task.must_continue_points) }}</el-descriptions-item>
      <el-descriptions-item label="禁止跳跃点">{{ joinList(task.forbidden_jumps) }}</el-descriptions-item>
      <el-descriptions-item label="伏笔动作">{{ task.required_foreshadowing_action || '暂无' }}</el-descriptions-item>
      <el-descriptions-item label="钩子强度">{{ task.required_hook_strength || '暂无' }}</el-descriptions-item>
      <el-descriptions-item label="节奏目标">{{ task.pace_target || '暂无' }}</el-descriptions-item>
      <el-descriptions-item label="开头承接">{{ task.opening_continuation || '暂无' }}</el-descriptions-item>
      <el-descriptions-item label="本章 Payoff">{{ task.chapter_payoff || '暂无' }}</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { formatChapterFunction } from '@/constants/display'

const props = defineProps({
  task: {
    type: Object,
    default: () => ({})
  },
  title: {
    type: String,
    default: '本章任务摘要'
  }
})

const hasTask = computed(() => Object.keys(props.task || {}).length > 0)

const joinList = (value) => {
  const items = Array.isArray(value) ? value.filter(Boolean) : []
  return items.length ? items.join('；') : '暂无'
}
</script>

<style scoped>
.chapter-task-card {
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.eyebrow {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9CA3AF;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.empty-text {
  color: #9CA3AF;
}
</style>
