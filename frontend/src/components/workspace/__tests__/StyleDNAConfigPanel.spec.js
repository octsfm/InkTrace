import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StyleDNAConfigPanel from '../StyleDNAConfigPanel.vue'

describe('StyleDNAConfigPanel', () => {
  it('renders active profile summary and low confidence warning', () => {
    const wrapper = mount(StyleDNAConfigPanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        extracting: false,
        extractJobActive: false,
        draftText: '这是标杆文本',
        draftSourceType: 'user_upload',
        activeProfile: {
          profile_id: 'sp_active_001',
          status: 'active',
          confidence: 0.42,
          low_confidence_reason: 'source_text_too_short',
          dialogue_ratio: 0.31,
          avg_sentence_length: 15.4,
          style_summary: '短句为主，动作感偏强。',
          style_tags: ['短句', '动作']
        },
        historyProfiles: [
          { profile_id: 'sp_active_001', status: 'active', version: 1 }
        ]
      }
    })

    expect(wrapper.text()).toContain('风格画像')
    expect(wrapper.text()).toContain('上传样章文本，提取结构化文风特征，并由你决定是否激活。')
    expect(wrapper.text()).toContain('短句为主，动作感偏强。')
    expect(wrapper.text()).toContain('置信度较低')
    expect(wrapper.text()).toContain('当前画像置信度较低：source_text_too_short')
    expect(wrapper.text()).toContain('低置信度原因：source_text_too_short')
    expect(wrapper.text()).toContain('source_text_too_short')
    expect(wrapper.text()).toContain('对白占比')
    expect(wrapper.text()).toContain('平均句长')
  })

  it('emits extract, confirm, disable and delete actions', async () => {
    const wrapper = mount(StyleDNAConfigPanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        extracting: false,
        extractJobActive: false,
        draftText: '这是标杆文本',
        draftSourceType: 'user_upload',
        currentProfile: {
          profile_id: 'sp_pending_001',
          status: 'pending_confirm',
          confidence: 0.81,
          style_summary: '冷静克制。'
        },
        activeProfile: {
          profile_id: 'sp_active_001',
          status: 'active',
          confidence: 0.77,
          style_summary: '简洁冷峻。'
        },
        historyProfiles: [
          { profile_id: 'sp_pending_001', status: 'pending_confirm', version: 2 },
          { profile_id: 'sp_active_001', status: 'active', version: 1 }
        ]
      }
    })

    await wrapper.get('[data-test="style-dna-extract"]').trigger('click')
    await wrapper.get('[data-test="style-dna-confirm"]').trigger('click')
    await wrapper.get('[data-test="style-dna-disable"]').trigger('click')
    await wrapper.get('[data-test="style-dna-delete-pending"]').trigger('click')

    expect(wrapper.emitted('extract')).toHaveLength(1)
    expect(wrapper.emitted('confirm-profile')).toEqual([['sp_pending_001']])
    expect(wrapper.emitted('disable-profile')).toEqual([['sp_active_001']])
    expect(wrapper.emitted('delete-profile')).toEqual([['sp_pending_001']])
  })

  it('emits view-profile when user clicks a history profile entry', async () => {
    const wrapper = mount(StyleDNAConfigPanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        extracting: false,
        extractJobActive: false,
        draftText: '',
        currentProfile: {
          profile_id: 'sp_pending_002',
          status: 'pending_confirm',
          confidence: 0.65,
          dialogue_ratio: 0.22,
          avg_sentence_length: 18.6,
          style_summary: '当前查看画像。'
        },
        historyProfiles: [
          { profile_id: 'sp_pending_002', status: 'pending_confirm', version: 2 },
          { profile_id: 'sp_active_001', status: 'active', version: 1 }
        ]
      }
    })

    await wrapper.get('[data-test="style-dna-history-sp_active_001"]').trigger('click')

    expect(wrapper.emitted('view-profile')).toEqual([['sp_active_001']])
  })

  it('shows more structured metrics and highlights active/current history states', () => {
    const wrapper = mount(StyleDNAConfigPanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        extracting: false,
        extractJobActive: false,
        currentProfile: {
          profile_id: 'sp_pending_002',
          status: 'pending_confirm',
          confidence: 0.65,
          dialogue_ratio: 0.22,
          avg_sentence_length: 18.6,
          psychological_ratio: 0.18,
          action_ratio: 0.41,
          description_ratio: 0.19,
          narrative_perspective: 'third_person_limited',
          tense_preference: 'past',
          style_summary: '当前查看画像。'
        },
        activeProfile: {
          profile_id: 'sp_active_001',
          status: 'active',
          confidence: 0.81,
          dialogue_ratio: 0.31,
          avg_sentence_length: 16.4,
          psychological_ratio: 0.12,
          action_ratio: 0.27,
          description_ratio: 0.25,
          narrative_perspective: 'first_person',
          tense_preference: 'present',
          style_summary: '当前激活画像。'
        },
        historyProfiles: [
          { profile_id: 'sp_pending_002', status: 'pending_confirm', version: 2 },
          { profile_id: 'sp_active_001', status: 'active', version: 1 },
          { profile_id: 'sp_archived_001', status: 'archived', version: 0 }
        ]
      }
    })

    expect(wrapper.text()).toContain('心理描写占比')
    expect(wrapper.text()).toContain('动作描写占比')
    expect(wrapper.text()).toContain('环境描写占比')
    expect(wrapper.text()).toContain('叙述视角')
    expect(wrapper.text()).toContain('时态偏好')
    expect(wrapper.text()).toContain('待确认')
    expect(wrapper.text()).toContain('已激活')
    expect(wrapper.text()).toContain('已归档')
    expect(wrapper.get('[data-test="style-dna-history-sp_pending_002"]').classes()).toContain('style-dna-panel__history-item--current')
    expect(wrapper.get('[data-test="style-dna-history-sp_active_001"]').classes()).toContain('style-dna-panel__history-item--active')
  })

  it('shows chapter reference options and limits selection copy to three chapters', () => {
    const wrapper = mount(StyleDNAConfigPanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: false,
        loading: false,
        extracting: false,
        extractJobActive: false,
        draftText: '',
        sourceMode: 'chapter_reference',
        selectedChapterIds: ['chapter-1', 'chapter-2', 'chapter-4'],
        chapterOptions: [
          { id: 'chapter-1', label: '第1章 起点', disabled: false },
          { id: 'chapter-2', label: '第2章 转折', disabled: false },
          { id: 'chapter-3', label: '第3章 草稿', disabled: true },
          { id: 'chapter-4', label: '第4章 落点', disabled: false }
        ],
        historyProfiles: []
      }
    })

    expect(wrapper.text()).toContain('从已有章节选择')
    expect(wrapper.text()).toContain('最多选择 3 章')
    expect(wrapper.text()).toContain('第3章 草稿')
    expect(wrapper.find('[data-test="style-dna-input"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="style-dna-chapter-option-chapter-3"]').attributes('disabled')).toBeDefined()
  })

  it('uses chinese punctuation in blocked and loading helper copy', () => {
    const wrapper = mount(StyleDNAConfigPanel, {
      props: {
        featureEnabled: true,
        aiSettingsBlocked: true,
        loading: false,
        extracting: true,
        extractJobActive: true,
        draftText: '这是标杆文本',
        sourceMode: 'chapter_reference',
        chapterOptions: [],
        selectedChapterIds: [],
        historyProfiles: []
      }
    })

    expect(wrapper.text()).toContain('请先配置可用模型服务与任务模型，再提取风格画像。')
    expect(wrapper.text()).toContain('仅限已确认章节，最多选择 3 章；草稿章节不可作为样章来源。')
    expect(wrapper.text()).toContain('提取中，请稍候')
    expect(wrapper.text()).not.toContain('请先配置可用模型服务与任务模型,再提取风格画像。')
    expect(wrapper.text()).not.toContain('仅限已确认章节,最多选择 3 章;草稿章节不可作为样章来源。')
    expect(wrapper.text()).not.toContain('提取中,请稍候')
  })
})
