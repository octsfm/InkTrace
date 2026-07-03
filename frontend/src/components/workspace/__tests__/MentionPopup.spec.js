import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MentionPopup from '../MentionPopup.vue'

describe('MentionPopup', () => {
  it('renders grouped mention suggestions and emits selection', async () => {
    const wrapper = mount(MentionPopup, {
      props: {
        visible: true,
        suggestions: [{
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name: '张三',
          summary_preview: '主角'
        }, {
          entity_type: 'event',
          entity_id: 'event_001',
          entity_name: '雨夜决战',
          summary_preview: '转折事件'
        }]
      }
    })

    expect(wrapper.text()).toContain('人物')
    expect(wrapper.text()).toContain('事件')
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('雨夜决战')

    await wrapper.get('[data-test="mention-popup-option-char_001"]').trigger('click')

    expect(wrapper.emitted('select')).toEqual([[{
      entity_type: 'character',
      entity_id: 'char_001',
      entity_name: '张三',
      summary_preview: '主角'
    }]])
  })

  it('stays hidden when popup visibility is disabled', () => {
    const wrapper = mount(MentionPopup, {
      props: {
        visible: false,
        suggestions: []
      }
    })

    expect(wrapper.find('[data-test="mention-popup"]').exists()).toBe(false)
  })
})
