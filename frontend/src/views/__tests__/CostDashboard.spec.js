import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api', () => ({ aiApi: {
  getCostSummary: vi.fn().mockResolvedValue({ data: { estimated_cost: '12.500000', currency: 'CNY', total_tokens: 42000, call_count: 8, cost_completeness: 'known' } }),
  getCostBudgets: vi.fn().mockResolvedValue({ data: { policies: [{ budget_type: 'monthly', enabled: true, limit: '50.000000', currency: 'CNY', revision: 1 }] } }),
  getCostDetails: vi.fn().mockResolvedValue({ data: { items: [] } }),
  getCostTrend: vi.fn().mockResolvedValue({ data: { items: [] } }),
  reconcileCostUsage: vi.fn(),
  updateCostBudget: vi.fn()
} }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: 'work-1' } }), useRouter: () => ({ push: vi.fn() }) }))

import CostDashboard from '../CostDashboard.vue'

describe('CostDashboard', () => {
  it('先告诉写手花了多少和还剩多少', async () => {
    const wrapper = mount(CostDashboard)
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('AI 用量与预算')
    expect(wrapper.text()).toContain('¥12.50')
    expect(wrapper.text()).toContain('¥37.50')
    expect(wrapper.text()).toContain('可能与 AI 服务商的最终账单略有不同')
  })
})
