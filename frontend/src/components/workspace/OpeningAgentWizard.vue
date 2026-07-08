<template>
  <div v-if="visible" class="opening-agent-wizard" data-test="opening-agent-wizard">
    <div class="opening-agent-wizard__backdrop" @click="$emit('close')"></div>
    <div class="opening-agent-wizard__dialog" role="dialog" aria-modal="true">
      <header class="opening-agent-wizard__header">
        <div>
          <h4>开篇助手</h4>
          <p>导入参考、分析开篇特点、确认策略与风险后，再进入正式候选稿生成链路。</p>
        </div>
        <button type="button" class="ink-button ink-button--ghost" data-test="opening-close" @click="$emit('close')">关闭</button>
      </header>

      <ol class="opening-agent-wizard__steps">
        <li
          v-for="(step, index) in steps"
          :key="step.id"
          class="opening-agent-wizard__step"
          :class="{ 'opening-agent-wizard__step--active': currentStep === index }"
        >
          {{ index + 1 }}. {{ step.label }}
        </li>
      </ol>

      <section class="opening-agent-wizard__content" data-test="opening-step">
        <template v-if="currentStep === 0">
          <h5>导入参考</h5>
          <p class="opening-agent-wizard__note">请先确认你拥有参考文本的合法使用权，确认后才能进入下一步。</p>
          <label class="opening-agent-wizard__checkbox">
            <input data-test="opening-rights-confirm-step1" type="checkbox" v-model="rightsConfirmedStep1">
            <span>我确认对参考文本拥有合法使用权</span>
          </label>
        </template>

        <template v-else-if="currentStep === 1">
          <h5>分析开篇特点</h5>
          <p class="opening-agent-wizard__note">这里展示开篇分析的最小结果摘要，不展示参考全文。</p>
          <div class="opening-agent-wizard__card" data-test="opening-analysis-summary">
            <strong>分析摘要</strong>
            <span>{{ openingAnalysis.analysis_summary }}</span>
          </div>
          <div class="opening-agent-wizard__card" data-test="opening-analysis-hooks">
            <strong>钩子模式</strong>
            <ul class="opening-agent-wizard__list">
              <li v-for="item in openingAnalysis.hook_patterns" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="opening-agent-wizard__card">
            <strong>冲突模式</strong>
            <ul class="opening-agent-wizard__list">
              <li v-for="item in openingAnalysis.conflict_patterns" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="opening-agent-wizard__card">
            <strong>爽点分布</strong>
            <ul class="opening-agent-wizard__list">
              <li v-for="item in openingAnalysis.satisfaction_points" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="opening-agent-wizard__card">
            <strong>章尾悬念</strong>
            <ul class="opening-agent-wizard__list">
              <li v-for="item in openingAnalysis.chapter_end_hooks" :key="item">{{ item }}</li>
            </ul>
          </div>
        </template>

        <template v-else-if="currentStep === 2">
          <h5>选择策略</h5>
          <p class="opening-agent-wizard__note">当前展示开篇策略的冻结摘要；确认后才允许进入风险确认。</p>
          <div class="opening-agent-wizard__card" data-test="opening-strategy-card">
            <strong>目标读者</strong>
            <span>{{ openingStrategy.target_audience }}</span>
            <strong>类型定位</strong>
            <span>{{ openingStrategy.genre_positioning }}</span>
            <strong>开篇钩子</strong>
            <span>{{ openingStrategy.opening_hook }}</span>
            <strong>前三章目标</strong>
            <span>{{ openingStrategy.first_three_chapter_goal }}</span>
            <strong>主角登场</strong>
            <span>{{ openingStrategy.protagonist_entry }}</span>
            <strong>冲突引入</strong>
            <span>{{ openingStrategy.conflict_entry }}</span>
            <strong>签约卖点</strong>
            <ul class="opening-agent-wizard__list">
              <li v-for="item in openingStrategy.selling_points" :key="item">{{ item }}</li>
            </ul>
            <strong>禁止模仿点</strong>
            <span>{{ openingStrategy.forbidden_similarity_notes }}</span>
          </div>
          <label class="opening-agent-wizard__checkbox">
            <input data-test="opening-strategy-confirm" type="checkbox" v-model="strategyConfirmed">
            <span>我已确认当前开篇策略方向</span>
          </label>
        </template>

        <template v-else>
          <h5>风险确认</h5>
          <p
            v-if="isHighRisk"
            class="opening-agent-wizard__risk opening-agent-wizard__risk--high"
          >
            存在较高的模仿风险，建议返回修改策略后再生成。
          </p>
          <p v-else class="opening-agent-wizard__risk">
            {{ riskSummary }}
          </p>
          <label class="opening-agent-wizard__checkbox">
            <input data-test="opening-rights-confirm-step4" type="checkbox" v-model="rightsConfirmedStep4">
            <span>我再次确认参考文本使用权与风险提示</span>
          </label>
        </template>
      </section>

      <footer class="opening-agent-wizard__footer">
        <button
          type="button"
          class="ink-button ink-button--ghost"
          data-test="opening-prev"
          :disabled="currentStep === 0"
          @click="currentStep -= 1"
        >
          上一步
        </button>

        <button
          v-if="currentStep < steps.length - 1"
          type="button"
          class="ink-button ink-button--primary"
          data-test="opening-next"
          :disabled="nextDisabled"
          @click="currentStep += 1"
        >
          下一步
        </button>

        <button
          v-else-if="isHighRisk"
          type="button"
          class="ink-button ink-button--ghost"
          data-test="opening-return-modify"
          @click="currentStep = 2"
        >
          返回修改
        </button>

        <button
          v-else
          type="button"
          class="ink-button ink-button--primary"
          data-test="opening-generate"
          :disabled="generateDisabled"
          @click="$emit('generate')"
        >
          {{ generateLabel }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  riskLevel: {
    type: String,
    default: 'warning'
  },
  analysis: {
    type: Object,
    default: () => ({})
  },
  strategy: {
    type: Object,
    default: () => ({})
  }
})

defineEmits(['close', 'generate'])

const steps = [
  { id: 'import', label: '导入参考' },
  { id: 'analyze', label: '分析特点' },
  { id: 'strategy', label: '选择策略' },
  { id: 'risk', label: '风险确认' }
]

const currentStep = ref(0)
const rightsConfirmedStep1 = ref(false)
const strategyConfirmed = ref(false)
const rightsConfirmedStep4 = ref(false)

const openingAnalysis = computed(() => ({
  analysis_summary: '参考作通常在前三章快速建立悬念，并持续抛出新的未解问题。',
  hook_patterns: ['前 500 字引入异常事件'],
  conflict_patterns: ['主角被迫卷入核心冲突'],
  satisfaction_points: ['节奏快、线索密集'],
  chapter_end_hooks: ['章尾抛出新的关键疑点'],
  ...(props.analysis || {})
}))

const openingStrategy = computed(() => ({
  target_audience: '签约向悬疑读者',
  genre_positioning: '都市悬疑',
  opening_hook: '用异常事件快速抓住读者',
  first_three_chapter_goal: '三章内建立主角、主冲突与核心悬念',
  protagonist_entry: '第一章前半段完成登场',
  conflict_entry: '第一章结尾抛出不可回避的主冲突',
  selling_points: ['节奏快', '悬念强'],
  forbidden_similarity_notes: '避免直接复用参考作的关键设定与场景编排',
  ...(props.strategy || {})
}))

const normalizedRiskLevel = computed(() => String(props.riskLevel || 'warning').toLowerCase())
const isHighRisk = computed(() => ['high', 'blocking'].includes(normalizedRiskLevel.value))

const riskSummary = computed(() => {
  if (normalizedRiskLevel.value === 'low') return '当前风险较低，确认后可以继续生成。'
  if (normalizedRiskLevel.value === 'medium') return '当前存在中等风险，建议确认策略后再继续生成。'
  return '当前存在提示级风险，请确认你已理解风险再继续生成。'
})

const nextDisabled = computed(() => {
  if (currentStep.value === 0) return !rightsConfirmedStep1.value
  if (currentStep.value === 2) return !strategyConfirmed.value
  return false
})

const generateDisabled = computed(() => !rightsConfirmedStep4.value)
const generateLabel = computed(() => '了解风险，继续生成')

const resetWizard = () => {
  currentStep.value = 0
  rightsConfirmedStep1.value = false
  strategyConfirmed.value = false
  rightsConfirmedStep4.value = false
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetWizard()
    }
  }
)
</script>

<style scoped>
.opening-agent-wizard {
  position: fixed;
  inset: 0;
  z-index: 60;
}

.opening-agent-wizard__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
}

.opening-agent-wizard__dialog {
  position: relative;
  width: min(860px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  margin: 24px auto;
  overflow: auto;
  border-radius: 24px;
  border: 1px solid var(--ink-border);
  background: var(--ink-surface-1);
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22);
}

.opening-agent-wizard__header,
.opening-agent-wizard__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 24px;
}

.opening-agent-wizard__header {
  border-bottom: 1px solid var(--ink-border);
}

.opening-agent-wizard__header h4,
.opening-agent-wizard__content h5 {
  margin: 0;
  color: var(--ink-text-primary);
}

.opening-agent-wizard__header p,
.opening-agent-wizard__note,
.opening-agent-wizard__risk,
.opening-agent-wizard__card span,
.opening-agent-wizard__card li {
  color: var(--ink-text-secondary);
}

.opening-agent-wizard__steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 16px 24px 0;
  list-style: none;
}

.opening-agent-wizard__step {
  border: 1px solid var(--ink-border);
  border-radius: 16px;
  padding: 10px 12px;
  color: var(--ink-text-muted);
  background: var(--ink-surface-2);
}

.opening-agent-wizard__step--active {
  border-color: var(--ink-accent);
  color: var(--ink-accent);
  background: color-mix(in srgb, var(--ink-accent) 10%, var(--ink-surface-1));
}

.opening-agent-wizard__content {
  display: grid;
  gap: 14px;
  padding: 20px 24px;
}

.opening-agent-wizard__card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--ink-border);
  border-radius: 18px;
  padding: 16px;
  background: var(--ink-surface-2);
}

.opening-agent-wizard__list {
  margin: 0;
  padding-left: 18px;
}

.opening-agent-wizard__checkbox {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  color: var(--ink-text-secondary);
}

.opening-agent-wizard__risk--high {
  color: var(--ink-danger-text);
  font-weight: 600;
}

.opening-agent-wizard__footer {
  border-top: 1px solid var(--ink-border);
}
</style>
