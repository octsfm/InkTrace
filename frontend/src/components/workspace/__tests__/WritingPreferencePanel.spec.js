import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WritingPreferencePanel from '../WritingPreferencePanel.vue'

describe('WritingPreferencePanel', () => {
  it('emits font family and theme updates from chip actions', async () => {
    const wrapper = mount(WritingPreferencePanel, {
      props: {
        preferences: {
          fontFamily: 'system-ui',
          fontSize: 18,
          lineHeight: 1.8,
          theme: 'light'
        }
      }
    })

    await wrapper.get('[data-test="font-monospace"]').trigger('click')
    await wrapper.get('[data-test="theme-dark"]').trigger('click')

    expect(wrapper.emitted('update-preferences')).toEqual([
      [{ fontFamily: 'monospace' }],
      [{ theme: 'dark' }]
    ])
  })

  it('emits font size and line height updates from selects', async () => {
    const wrapper = mount(WritingPreferencePanel, {
      props: {
        preferences: {
          fontFamily: 'serif',
          fontSize: 20,
          lineHeight: 1.6,
          theme: 'warm'
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
