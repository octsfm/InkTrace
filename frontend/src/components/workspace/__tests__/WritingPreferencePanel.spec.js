import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WritingPreferencePanel from '../WritingPreferencePanel.vue'

describe('WritingPreferencePanel', () => {
  it('emits font family updates from chip actions', async () => {
    const wrapper = mount(WritingPreferencePanel, {
      props: {
        preferences: {
          fontFamily: 'system-ui',
          fontSize: 18,
          lineHeight: 1.8
        }
      }
    })

    await wrapper.get('[data-test="font-monospace"]').trigger('click')

    expect(wrapper.text()).toContain('这里只调整正文阅读体验，包括字体、字号和行高，不会修改全局界面主题和正文内容。')
    expect(wrapper.text()).not.toContain('这里只调整正文阅读体验,包括字体、字号和行高,不会修改全局界面主题和正文内容。')
    expect(wrapper.emitted('update-preferences')).toEqual([
      [{ fontFamily: 'monospace' }]
    ])
  })

  it('emits font size and line height updates from selects', async () => {
    const wrapper = mount(WritingPreferencePanel, {
      props: {
        preferences: {
          fontFamily: 'serif',
          fontSize: 20,
          lineHeight: 1.6
        }
      }
    })

    await wrapper.get('[data-test="font-size-select"]').setValue('24')
    await wrapper.get('[data-test="line-height-select"]').setValue('2')

    expect(wrapper.emitted('update-preferences')).toEqual([
      [{ fontSize: 24 }],
      [{ lineHeight: 2 }]
    ])
  })
})
