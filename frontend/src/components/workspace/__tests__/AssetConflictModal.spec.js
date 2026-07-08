import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AssetConflictModal from '../AssetConflictModal.vue'

describe('AssetConflictModal', () => {
  it('renders asset conflict copy when opened', () => {
    const wrapper = mount(AssetConflictModal, {
      props: {
        modelValue: true,
        description: 'Outline was modified elsewhere.'
      }
    })

    expect(wrapper.text()).toContain('资料版本冲突')
    expect(wrapper.text()).toContain('Outline was modified elsewhere.')
    expect(wrapper.text()).toContain('本地资料草稿会一直保留')
  })

  it('provides a local vs server compare entry', () => {
    const wrapper = mount(AssetConflictModal, {
      props: {
        modelValue: true,
        localContent: 'local outline draft',
        serverContent: 'server outline'
      }
    })

    expect(wrapper.find('.compare-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('展开查看本地版本与服务器版本对比')
    expect(wrapper.text()).toContain('本地版本')
    expect(wrapper.text()).toContain('local outline draft')
    expect(wrapper.text()).toContain('服务器版本')
    expect(wrapper.text()).toContain('server outline')
  })

  it('emits cancel discard and override decisions without clearing drafts itself', async () => {
    const wrapper = mount(AssetConflictModal, {
      props: { modelValue: true }
    })

    await wrapper.findAll('button')[0].trigger('click')
    await wrapper.findAll('button')[1].trigger('click')
    await wrapper.findAll('button')[2].trigger('click')

    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('discard')).toHaveLength(1)
    expect(wrapper.emitted('override')).toHaveLength(1)
  })

  it('does not render when closed', () => {
    const wrapper = mount(AssetConflictModal, {
      props: { modelValue: false }
    })

    expect(wrapper.find('.modal-mask').exists()).toBe(false)
  })
})
