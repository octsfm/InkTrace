import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AssetRail from '../AssetRail.vue'

describe('AssetRail', () => {
  it('renders the four non-AI writing asset entries', () => {
    const wrapper = mount(AssetRail)

    expect(wrapper.findAll('.asset-rail-button')).toHaveLength(4)
    expect(wrapper.text()).toContain('Outline')
    expect(wrapper.text()).toContain('Timeline')
    expect(wrapper.text()).toContain('Foreshadow')
    expect(wrapper.text()).toContain('Character')
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
