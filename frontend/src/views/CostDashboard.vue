<template>
  <main class="cost-page">
    <header class="page-header">
      <div><p class="eyebrow">写作助手</p><h1>AI 用量与预算</h1><p>先看花了多少，再决定要不要调整保护。</p></div>
      <button type="button" @click="goBack">回到写作</button>
    </header>
    <section v-if="loading" class="card">正在整理 AI 用量……</section>
    <section v-else-if="errorMessage" class="card"><p>{{ errorMessage }}</p><button type="button" @click="load">重新检查</button></section>
    <template v-else>
      <section class="summary-grid">
        <article class="card"><span>本月预计费用</span><strong>{{ costText }}</strong></article>
        <article class="card"><span>本月还剩</span><strong>{{ remainingText }}</strong></article>
        <article class="card"><span>预算状态</span><strong class="status">{{ budgetStatus }}</strong></article>
      </section>
      <section class="card budget-card">
        <div><h2>预算保护</h2><p>只影响现在和之后的 AI 操作，不会自动继续被暂停的任务。</p></div>
        <button type="button" @click="openSettings">调整预算</button>
      </section>
      <section class="card">
        <h2>本月用量</h2>
        <p>共使用 {{ number(summary.call_count) }} 次，约 {{ number(summary.total_tokens) }} AI 用量单位。</p>
        <p v-if="summary.cost_completeness !== 'known'" class="notice">有些使用没有保留当时的价格，系统不会用现在的价格倒推。</p>
        <button v-if="summary.cost_completeness === 'unknown' || summary.usage_completeness === 'unknown'" type="button" :disabled="repairing" @click="repairUsage">{{ repairing ? '正在检查……' : '重新检查并尝试修复' }}</button>
      </section>
      <section class="card"><h2>最近用量</h2><ul class="usage-list"><li v-for="item in trend" :key="item.date"><span>{{ item.date }}</span><span>{{ number(item.call_count) }} 次</span><span>{{ item.estimated_cost == null ? '费用不明' : money(item.estimated_cost, summary.currency || 'CNY') }}</span></li></ul></section>
      <section class="card"><h2>使用明细</h2><p v-if="!details.length" class="notice">这个月还没有 AI 使用记录。</p><ul v-else class="usage-list"><li v-for="(item,index) in details" :key="`${item.started_at}-${index}`"><span>{{ new Date(item.started_at).toLocaleString('zh-CN') }}</span><span>{{ number(item.total_tokens) }} 用量</span><span>{{ item.estimated_cost == null ? '费用不明' : money(item.estimated_cost,item.currency || 'CNY') }}</span></li></ul></section>
      <p class="footnote">根据每次使用时保存的价格估算，可能与 AI 服务商的最终账单略有不同。</p>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { aiApi } from '@/api'

const route = useRoute(); const router = useRouter(); const loading = ref(true); const errorMessage = ref(''); const summary = ref({}); const policies = ref([]); const trend=ref([]); const details=ref([]); const repairing=ref(false)
const unwrap = (value) => value?.data?.data ?? value?.data ?? value ?? {}
const monthly = computed(() => policies.value.find((item) => item.budget_type === 'monthly'))
const number = (value) => Number(value || 0).toLocaleString('zh-CN')
const money = (value, currency = 'CNY') => value == null ? '暂时无法确认' : new Intl.NumberFormat('zh-CN', { style: 'currency', currency, minimumFractionDigits: 2 }).format(Number(value))
const costText = computed(() => money(summary.value.estimated_cost, summary.value.currency || monthly.value?.currency || 'CNY'))
const remainingText = computed(() => !monthly.value?.enabled || summary.value.estimated_cost == null ? '未设置可比较的保护' : money(Math.max(Number(monthly.value.limit) - Number(summary.value.estimated_cost), 0), monthly.value.currency))
const budgetStatus = computed(() => !monthly.value?.enabled ? '未设置保护' : summary.value.estimated_cost == null ? '暂时无法确认' : Number(summary.value.estimated_cost) >= Number(monthly.value.limit) ? '已到上限' : Number(summary.value.estimated_cost) >= Number(monthly.value.limit) * Number(monthly.value.alert_threshold || 0.8) ? '接近上限' : '目前未到上限')
const load = async () => { loading.value=true; errorMessage.value=''; try { const workId=String(route.params.id||''); const now=new Date(); const to=now.toISOString().slice(0,10); const from=new Date(now.getTime()-29*86400000).toISOString().slice(0,10); const [usage,budget,trendResponse,detailResponse]=await Promise.all([aiApi.getCostSummary(workId),aiApi.getCostBudgets(workId),aiApi.getCostTrend(workId,from,to),aiApi.getCostDetails(workId)]); summary.value=unwrap(usage); policies.value=unwrap(budget).policies||[]; trend.value=unwrap(trendResponse).items||[]; details.value=unwrap(detailResponse).items||[] } catch(error) { errorMessage.value=error?.userMessage||'预算状态暂时没有加载出来。新的 AI 操作先停一下，请稍后重新检查。' } finally { loading.value=false } }
const repairUsage=async()=>{repairing.value=true;try{await aiApi.reconcileCostUsage({work_id:String(route.params.id||''),caller_type:'user_action',user_action:true,user_id:'local-author',idempotency_key:`reconcile-${Date.now()}`});await load()}catch(error){errorMessage.value=error?.userMessage||'无法自动修复这些记录，系统不会猜测用量或费用。'}finally{repairing.value=false}}
const goBack = () => router.push(`/works/${encodeURIComponent(String(route.params.id || ''))}`)
const openSettings = () => router.push({ path: '/settings', query: { section: 'ai-cost', work_id: String(route.params.id || '') } })
onMounted(load)
</script>

<style scoped>
.cost-page { min-height: 100vh; padding: 32px; background: var(--ink-bg-app); color: var(--ink-text-primary); }.page-header,.summary-grid,.card,.footnote{max-width:1120px;margin-left:auto;margin-right:auto}.page-header{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:24px}.page-header h1{margin:4px 0 8px;font-size:32px}.page-header p,.budget-card p,.footnote{color:var(--ink-text-secondary)}.eyebrow{color:var(--ink-accent)!important;font-weight:700}.page-header button,.budget-card button,.card button{border:1px solid var(--ink-border);border-radius:12px;background:var(--ink-surface-1);color:var(--ink-text-primary);padding:10px 16px;cursor:pointer}.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:16px}.card{box-sizing:border-box;border:1px solid var(--ink-border);border-radius:20px;background:var(--ink-surface-1);padding:22px;margin-bottom:16px}.summary-grid .card{margin-bottom:0}.card span{color:var(--ink-text-secondary)}.card strong{display:block;margin-top:10px;font-size:28px}.status{font-size:20px!important}.budget-card{display:flex;align-items:center;justify-content:space-between;gap:24px}.budget-card h2{margin-top:0}.notice{padding:14px;border-radius:12px;background:var(--ink-bg-app)}.footnote{font-size:13px}@media(max-width:760px){.cost-page{padding:20px 16px}.page-header,.budget-card{align-items:flex-start;flex-direction:column}.summary-grid{grid-template-columns:1fr}}
.usage-list{list-style:none;padding:0;margin:0;display:grid;gap:8px}.usage-list li{display:grid;grid-template-columns:1fr auto auto;gap:18px;padding:12px;border-radius:10px;background:var(--ink-bg-app)}
</style>
