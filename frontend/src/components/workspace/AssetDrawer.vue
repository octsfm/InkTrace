<template>
  <aside v-if="visible" class="asset-drawer">
    <div class="asset-drawer-header">
      <div>
        <h3>{{ activeLabel }}</h3>
        <p>当前阶段先挂载单抽屉入口，后续继续补资产编辑表单。</p>
      </div>
      <button type="button" class="close-button" @click="$emit('close')">关闭</button>
    </div>
    <div class="asset-drawer-body">
      <p>{{ bodyText }}</p>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  activeTab: {
    type: String,
    default: ''
  }
})

defineEmits(['close'])

const labelMap = {
  outline: '大纲',
  timeline: '时间线',
  foreshadow: '伏笔',
  character: '人物'
}

const activeLabel = computed(() => labelMap[String(props.activeTab || '')] || '结构化资产')
const bodyText = computed(() => `${activeLabel.value} 抽屉已挂载，后续将在这里继续补显式保存和冲突处理。`)
</script>

<style scoped>
.asset-drawer {
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: #ffffff;
  padding: 18px;
}

.asset-drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.asset-drawer-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.asset-drawer-header p,
.asset-drawer-body p {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #6b7280;
}

.close-button {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #ffffff;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.asset-drawer-body {
  margin-top: 18px;
}
</style>
