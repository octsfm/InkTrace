import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AssetDrawer from '../AssetDrawer.vue'

describe('AssetDrawer', () => {
  it('renders one active drawer with header title and no duplicate tab strip', () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'outline'
      }
    })

    expect(wrapper.findAll('.asset-drawer')).toHaveLength(1)
    expect(wrapper.find('.asset-drawer-header h3').text()).toBe('大纲')
    expect(wrapper.findAll('[data-asset-tab]')).toHaveLength(0)
  })

  it('switches directly through the exposed requestSwitch method when current tab is clean', async () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'outline',
        dirtyTabs: []
      }
    })

    await wrapper.vm.requestSwitch('timeline')

    expect(wrapper.emitted('switch')?.[0]).toEqual(['timeline'])
    expect(wrapper.find('.dirty-guard').exists()).toBe(false)
  })

  it('guards dirty module switching with save discard cancel branches', async () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'outline',
        dirtyTabs: ['outline']
      }
    })

    await wrapper.vm.requestSwitch('timeline')
    expect(wrapper.find('.dirty-guard').exists()).toBe(true)

    await wrapper.findAll('.dirty-guard-actions button')[2].trigger('click')
    expect(wrapper.emitted('switch')).toBeUndefined()
    expect(wrapper.find('.dirty-guard').exists()).toBe(false)

    await wrapper.vm.requestSwitch('timeline')
    await wrapper.findAll('.dirty-guard-actions button')[0].trigger('click')
    expect(wrapper.emitted('save-dirty')?.[0]).toEqual(['outline'])
    expect(wrapper.emitted('switch')?.[0]).toEqual(['timeline'])
  })

  it('guards dirty close and supports discard branch', async () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'character',
        dirtyTabs: ['character']
      }
    })

    await wrapper.find('.close-button').trigger('click')
    expect(wrapper.find('.dirty-guard').exists()).toBe(true)

    await wrapper.findAll('.dirty-guard-actions button')[1].trigger('click')
    expect(wrapper.emitted('discard-dirty')?.[0]).toEqual(['character'])
    expect(wrapper.emitted('close')?.[0]).toEqual([])
  })

  it('uses header body footer layout hooks without creating a new page on mobile', () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'foreshadow',
        mobile: true
      },
      slots: {
        footer: '<div class="footer-slot">Footer</div>'
      }
    })

    expect(wrapper.find('.asset-drawer').classes()).toContain('mobile-overlay')
    expect(wrapper.find('.asset-drawer-body').exists()).toBe(true)
    expect(wrapper.find('.asset-drawer-footer').exists()).toBe(true)
    expect(wrapper.find('.footer-slot').exists()).toBe(true)
  })
})
