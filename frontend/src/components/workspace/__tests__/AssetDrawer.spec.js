import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AssetDrawer from '../AssetDrawer.vue'

describe('AssetDrawer', () => {
  it('renders one active tab inside a single drawer', () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'outline'
      }
    })

    expect(wrapper.findAll('.asset-drawer')).toHaveLength(1)
    expect(wrapper.find('[data-asset-tab="outline"]').classes()).toContain('active')
    expect(wrapper.find('[data-asset-tab="timeline"]').classes()).not.toContain('active')
  })

  it('switches directly when current tab is clean', async () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'outline',
        dirtyTabs: []
      }
    })

    await wrapper.find('[data-asset-tab="timeline"]').trigger('click')

    expect(wrapper.emitted('switch')?.[0]).toEqual(['timeline'])
    expect(wrapper.find('.dirty-guard').exists()).toBe(false)
  })

  it('guards dirty tab switching with save discard cancel branches', async () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'outline',
        dirtyTabs: ['outline']
      }
    })

    await wrapper.find('[data-asset-tab="timeline"]').trigger('click')
    expect(wrapper.find('.dirty-guard').exists()).toBe(true)

    await wrapper.findAll('.dirty-guard-actions button')[2].trigger('click')
    expect(wrapper.emitted('switch')).toBeUndefined()
    expect(wrapper.find('.dirty-guard').exists()).toBe(false)

    await wrapper.find('[data-asset-tab="timeline"]').trigger('click')
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

  it('uses mobile overlay without creating a new page', () => {
    const wrapper = mount(AssetDrawer, {
      props: {
        visible: true,
        activeTab: 'foreshadow',
        mobile: true
      }
    })

    expect(wrapper.find('.asset-drawer').classes()).toContain('mobile-overlay')
  })
})
