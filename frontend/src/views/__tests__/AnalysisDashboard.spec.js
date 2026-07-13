import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { responses } = vi.hoisted(() => ({ responses: {
  getAnalysisOverview: { data: { total_word_count: 32000, total_chapters: 12, daily_avg_words: 1200, ai_adoption_rate: 0.25, chapter_word_counts: [] } },
  getAnalysisRhythm: { data: { short_sentence_density: 0.3, chapter_word_count_std: 120, cliffhanger_stats: { per_chapter: [] } } },
  getAnalysisDialogue: { data: { dialogue_ratio: 0.4, avg_dialogue_length: 18, note: '仅供参考' } },
  getAnalysisWordFrequency: { data: { words: [], total_unique_words: 800 } },
  getAnalysisStyle: { data: { consistency_score: 0.8, warning: 'no_active_style_profile', chapter_trend: [] } },
  getAnalysisAIUsage: { data: { adoption_rate: 0.25, avg_revision_rounds: 1.2, ai_word_frequency: [], disclaimer: 'AI 常见词汇仅统计出现频率，不代表文本一定由 AI 生成' } }
} }))

vi.mock('@/api', () => ({
  aiApi: Object.fromEntries(Object.entries(responses).map(([key, value]) => [key, vi.fn().mockResolvedValue(value)]))
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'work-1' } }),
  useRouter: () => ({ push: vi.fn() })
}))

import AnalysisDashboard from '../AnalysisDashboard.vue'

describe('AnalysisDashboard', () => {
  beforeEach(() => vi.clearAllMocks())

  it('用写手能看懂的话解释分析，不判定文本作者', async () => {
    const wrapper = mount(AnalysisDashboard)
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('创作分析')
    expect(wrapper.text()).toContain('32,000')
    expect(wrapper.text()).toContain('不代表文本一定由 AI 生成')
    expect(wrapper.text()).not.toContain('AI 生成嫌疑')
  })
})
