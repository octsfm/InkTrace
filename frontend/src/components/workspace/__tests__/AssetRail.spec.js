import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AssetRail from '../AssetRail.vue'

describe('AssetRail', () => {
  it('renders four single-character non-AI writing asset entries with full labels in accessibility attrs', () => {
    const wrapper = mount(AssetRail)

    const buttons = wrapper.findAll('.asset-rail-button')
    expect(buttons).toHaveLength(4)
    expect(buttons.map((button) => button.text())).toEqual(['纲', '线', '伏', '人'])
    expect(wrapper.find('[data-asset-tab="outline"]').attributes('title')).toBe('大纲')
    expect(wrapper.find('[data-asset-tab="timeline"]').attributes('aria-label')).toBe('时间线')
    expect(wrapper.find('[data-asset-tab="foreshadow"]').attributes('title')).toBe('伏笔')
    expect(wrapper.find('[data-asset-tab="character"]').attributes('aria-label')).toBe('人物')
  })

  it('emits selected tab when clicking an inactive entry', async () => {
    const wrapper = mount(AssetRail, {
      props: {
        activeTab: ''
      }
    })

    await wrapper.find('[data-asset-tab="timeline"]').trigger('click')

    expect(wrapper.emitted('toggle')?.[0]).toEqual(['timeline'])
  })

  it('emits empty tab when clicking the active entry again', async () => {
    const wrapper = mount(AssetRail, {
      props: {
        activeTab: 'outline'
      }
    })

    await wrapper.find('[data-asset-tab="outline"]').trigger('click')

    expect(wrapper.emitted('toggle')?.[0]).toEqual([''])
  })

  it('hides the active entry when configured by the drawer host', () => {
    const wrapper = mount(AssetRail, {
      props: {
        activeTab: 'outline',
        hideActiveEntry: true
      }
    })

    expect(wrapper.find('[data-asset-tab="outline"]').exists()).toBe(false)
    expect(wrapper.findAll('.asset-rail-button')).toHaveLength(3)
    expect(wrapper.find('[data-asset-tab="timeline"]').exists()).toBe(true)
  })

  it('marks active entry without touching editor state', () => {
    const wrapper = mount(AssetRail, {
      props: {
        activeTab: 'character'
      }
    })

    expect(wrapper.find('[data-asset-tab="character"]').classes()).toContain('active')
    expect(wrapper.find('[data-asset-tab="character"]').attributes('aria-pressed')).toBe('true')
  })
})
