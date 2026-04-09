<template>
  <el-card shadow="never" class="context-source-panel">
    <template #header>
      <div>
        <div class="eyebrow">Context</div>
        <span class="panel-title">本次 AI 参考了</span>
      </div>
    </template>
    <el-collapse>
      <el-collapse-item title="最近章节" name="recent">
        <div class="meta-line">最近章节数：{{ recentChapterCount }}</div>
        <div class="meta-line">上一章尾部长度：{{ lastTailLength }} 字</div>
      </el-collapse-item>
      <el-collapse-item title="本章结构" name="outline">
        <div class="meta-line">本章大纲：{{ hasOutline ? '已提供' : '未提供' }}</div>
        <div class="meta-line">本章任务：{{ hasTask ? '已提供' : '未提供' }}</div>
      </el-collapse-item>
      <el-collapse-item title="角色与伏笔" name="actors">
        <div class="meta-line">相关角色：{{ characterCount }} 个</div>
        <div class="meta-line">相关伏笔：{{ foreshadowingCount }} 条</div>
      </el-collapse-item>
      <el-collapse-item title="全书约束" name="constraints">
        <div class="meta-line">主线摘要：{{ mainPlotText }}</div>
        <div class="meta-line">必须保留线索：{{ mustKeepCount }} 条</div>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  context: {
    type: Object,
    default: () => ({})
  },
  task: {
    type: Object,
    default: () => ({})
  }
})

const recentChapterCount = computed(() => (props.context.recent_chapter_memories || []).length)
const lastTailLength = computed(() => String(props.context.last_chapter_tail || '').length)
const characterCount = computed(() => (props.context.relevant_characters || []).length)
const foreshadowingCount = computed(() => (props.context.relevant_foreshadowing || []).length)
const mustKeepCount = computed(() => ((props.context.global_constraints || {}).must_keep_threads || []).length)
const hasTask = computed(() => Object.keys(props.task || {}).length > 0)
const hasOutline = computed(() => Object.keys(props.context.chapter_outline || {}).length > 0)
const mainPlotText = computed(() => String((props.context.global_constraints || {}).main_plot || '暂无'))
</script>

<style scoped>
.context-source-panel {
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

.meta-line {
  margin-bottom: 8px;
  color: #4B5563;
  line-height: 1.6;
}
</style>
