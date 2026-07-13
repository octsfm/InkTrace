<template>
  <main class="analysis-page">
    <header class="analysis-header">
      <div>
        <p class="eyebrow">写作助手</p>
        <h1>创作分析</h1>
        <p>只做统计和提醒，帮你看清写作节奏，不替你做判断。</p>
      </div>
      <div class="header-buttons"><button type="button" class="back-button" :disabled="refreshing" @click="refreshAll">{{ refreshing ? '正在重新统计……' : '重新统计' }}</button><button type="button" class="back-button" @click="goBack">回到写作</button></div>
    </header>

    <section v-if="loading" class="state-card">正在整理你的作品……</section>
    <section v-else-if="errorMessage" class="state-card state-card--error">
      <p>{{ errorMessage }}</p>
      <button type="button" class="back-button" @click="loadAnalysis">重新试试</button>
    </section>

    <template v-else>
      <section v-if="hasStaleData" class="state-card stale-card">
        <span>部分数据来自较早的正文，可能已经过期。</span>
        <button type="button" class="back-button" :disabled="refreshing" @click="refreshAll">重新统计</button>
      </section>
      <p v-if="cachedComputedAt" class="cache-label">缓存数据 · {{ new Date(cachedComputedAt).toLocaleString('zh-CN') }}</p>
      <section class="summary-grid" aria-label="作品概况">
        <article class="metric-card">
          <span>已写字数</span>
          <strong>{{ number(overview.total_word_count) }}</strong>
        </article>
        <article class="metric-card">
          <span>章节数</span>
          <strong>{{ number(overview.total_chapters) }}</strong>
        </article>
        <article class="metric-card">
          <span>日均新增</span>
          <strong>{{ number(overview.daily_avg_words) }}</strong>
        </article>
        <article class="metric-card">
          <span>采用过 AI 候选稿</span>
          <strong>{{ percent(aiUsage.adoption_rate ?? overview.ai_adoption_rate) }}</strong>
        </article>
      </section>

      <nav class="analysis-tabs" aria-label="分析项目">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <section class="detail-card">
        <template v-if="activeTab === 'rhythm'">
          <h2>叙事节奏</h2>
          <p>短句占比 {{ percent(rhythm.short_sentence_density) }}，各章字数波动约 {{ number(rhythm.chapter_word_count_std) }} 字。</p>
          <p class="helper">数值没有标准答案，只用来帮你发现某些章节是否过长或过短。</p>
        </template>
        <template v-else-if="activeTab === 'dialogue'">
          <h2>对话情况</h2>
          <p>对话约占 {{ percent(dialogue.dialogue_ratio) }}，平均每段 {{ number(dialogue.avg_dialogue_length) }} 字。</p>
          <p class="helper">{{ dialogue.note || '仅供你回顾节奏，不判断写法好坏。' }}</p>
        </template>
        <template v-else-if="activeTab === 'words'">
          <h2>常用词</h2>
          <p>共统计到 {{ number(wordFrequency.total_unique_words) }} 个不同词汇。</p>
          <ul v-if="wordFrequency.words?.length" class="word-list">
            <li v-for="item in wordFrequency.words.slice(0, 12)" :key="item.word">
              <span>{{ item.word }}</span><strong>{{ item.frequency }}</strong>
            </li>
          </ul>
          <p v-else class="helper">内容还不够多，暂时没有可展示的常用词。</p>
        </template>
        <template v-else-if="activeTab === 'style'">
          <h2>风格稳定度</h2>
          <p>当前参考分数 {{ percent(style.consistency_score) }}。</p>
          <p class="helper">{{ style.warning === 'no_active_style_profile' ? '还没有确认风格样本，这个数字只能作为粗略参考。' : '用来帮你定位可能风格变化较大的章节。' }}</p>
        </template>
        <template v-else>
          <h2>AI 使用情况</h2>
          <p>候选稿采用率 {{ percent(aiUsage.adoption_rate) }}，平均修改 {{ number(aiUsage.avg_revision_rounds, 1) }} 轮。</p>
          <p class="disclaimer">{{ aiUsage.disclaimer || 'AI 常见词汇仅统计出现频率，不代表文本一定由 AI 生成。' }}</p>
        </template>
      </section>
      <p class="analysis-note">
        {{ aiUsage.disclaimer || 'AI 常见词汇仅统计出现频率，不代表文本一定由 AI 生成。' }}
      </p>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { aiApi } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const errorMessage = ref('')
const activeTab = ref('rhythm')
const overview = ref({})
const rhythm = ref({})
const dialogue = ref({})
const wordFrequency = ref({})
const style = ref({})
const aiUsage = ref({})
const refreshing = ref(false)
const responseMeta = ref([])
const tabs = [
  { key: 'rhythm', label: '节奏' },
  { key: 'dialogue', label: '对话' },
  { key: 'words', label: '常用词' },
  { key: 'style', label: '风格' },
  { key: 'ai', label: 'AI 使用' }
]

const extract = (response) => {
  const payload = response?.data?.data ?? response?.data ?? response ?? {}
  if (payload?.source && Object.prototype.hasOwnProperty.call(payload, 'data')) return payload
  return { source: 'realtime', computed_at: '', stale: false, data: payload }
}
const hasStaleData = computed(() => responseMeta.value.some((item) => item.stale))
const cachedComputedAt = computed(() => responseMeta.value.find((item) => item.source === 'cached')?.computed_at || '')
const number = (value, digits = 0) => Number(value || 0).toLocaleString('zh-CN', {
  minimumFractionDigits: digits,
  maximumFractionDigits: digits
})
const percent = (value) => `${Math.round(Number(value || 0) * 100)}%`

const loadAnalysis = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const workId = String(route.params.id || '')
    const results = await Promise.all([
      aiApi.getAnalysisOverview(workId),
      aiApi.getAnalysisRhythm(workId),
      aiApi.getAnalysisDialogue(workId),
      aiApi.getAnalysisWordFrequency(workId),
      aiApi.getAnalysisStyle(workId),
      aiApi.getAnalysisAIUsage(workId)
    ])
    const wrapped = results.map(extract)
    responseMeta.value = wrapped
    ;[overview.value, rhythm.value, dialogue.value, wordFrequency.value, style.value, aiUsage.value] = wrapped.map((item) => item.data || {})
  } catch (error) {
    errorMessage.value = error?.userMessage || '创作分析暂时打不开，你的正文不会受影响。'
  } finally {
    loading.value = false
  }
}

const goBack = () => router.push(`/works/${encodeURIComponent(String(route.params.id || ''))}`)
const refreshAll = async () => {
  refreshing.value=true
  try {
    const workId=String(route.params.id||'')
    await aiApi.refreshAnalysis({work_id:workId,caller_type:'user_action',user_action:true,user_id:'local-author',idempotency_key:`analysis-${Date.now()}-${Math.random().toString(36).slice(2,8)}`})
    for (let attempt=0;attempt<60;attempt+=1) {
      const status=extract(await aiApi.getAnalysisStatus(workId)).data
      if (status.status==='completed') break
      if (status.status==='failed') throw new Error('analysis recompute failed')
      await new Promise((resolve)=>setTimeout(resolve,250))
    }
    await loadAnalysis()
  }
  catch(error) { errorMessage.value=error?.userMessage||'重新统计失败，原来的分析结果还在。' }
  finally { refreshing.value=false }
}
onMounted(loadAnalysis)
</script>

<style scoped>
.analysis-page { min-height: 100vh; padding: 32px; background: var(--ink-bg-app); color: var(--ink-text-primary); }
.analysis-header { max-width: 1120px; margin: 0 auto 24px; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.analysis-header h1 { margin: 4px 0 8px; font-size: 32px; }
.analysis-header p { margin: 0; color: var(--ink-text-secondary); }
.header-buttons { display: flex; gap: 10px; }
.eyebrow { color: var(--ink-accent) !important; font-weight: 700; }
.back-button, .analysis-tabs button { border: 1px solid var(--ink-border); border-radius: 12px; background: var(--ink-surface-1); color: var(--ink-text-primary); padding: 10px 16px; cursor: pointer; }
.summary-grid { max-width: 1120px; margin: 0 auto 20px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.metric-card, .detail-card, .state-card { border: 1px solid var(--ink-border); border-radius: 20px; background: var(--ink-surface-1); padding: 22px; }
.metric-card span { display: block; color: var(--ink-text-secondary); font-size: 14px; }
.metric-card strong { display: block; margin-top: 10px; font-size: 28px; }
.analysis-tabs { max-width: 1120px; margin: 0 auto 16px; display: flex; gap: 8px; overflow-x: auto; }
.analysis-tabs button.active { border-color: var(--ink-accent); color: var(--ink-accent); background: var(--ink-accent-soft); }
.detail-card, .state-card { max-width: 1076px; margin: 0 auto; }
.analysis-note { max-width: 1076px; margin: 16px auto 0; color: var(--ink-text-secondary); font-size: 13px; }
.detail-card h2 { margin-top: 0; }
.helper, .disclaimer { color: var(--ink-text-secondary); line-height: 1.8; }
.disclaimer { margin-top: 20px; padding: 14px; border-radius: 12px; background: var(--ink-bg-app); }
.word-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 0; list-style: none; }
.word-list li { display: flex; justify-content: space-between; padding: 10px 12px; border-radius: 10px; background: var(--ink-bg-app); }
.state-card--error { color: var(--ink-danger); }
.stale-card { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; gap: 16px; background: #fffbeb; border-color: #f59e0b; }
.cache-label { max-width: 1120px; margin: 0 auto 12px; color: var(--ink-text-secondary); font-size: 12px; text-align: right; }
@media (max-width: 760px) { .analysis-page { padding: 20px 16px; } .analysis-header { align-items: flex-start; flex-direction: column; } .summary-grid { grid-template-columns: repeat(2, 1fr); } .word-list { grid-template-columns: 1fr; } }
</style>
