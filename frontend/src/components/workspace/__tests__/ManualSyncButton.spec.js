import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ManualSyncButton from '../ManualSyncButton.vue'

describe('ManualSyncButton', () => {
  it('renders idle and saving labels', async () => {
    const wrapper = mount(ManualSyncButton, {
      props: {
        saving: false
      }
    })

    expect(wrapper.text()).toContain('立即同步')

    await wrapper.setProps({ saving: true })
    expect(wrapper.text()).toContain('同步中...')
  })

  it('emits sync click when enabled', async () => {
    const wrapper = mount(ManualSyncButton)

    await wrapper.get('[data-test="manual-sync-button"]').trigger('click')

    expect(wrapper.emitted('sync')).toHaveLength(1)
  })
})
