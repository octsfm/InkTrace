import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RightWorkspacePanel from '../RightWorkspacePanel.vue'

describe('RightWorkspacePanel', () => {
  it('renders six tabs and keeps review as a first-class workspace entry', () => {
    const wrapper = mount(RightWorkspacePanel, {
      props: {
        modelValue: 'review'
      }
    })

    const buttons = wrapper.findAll('[data-workspace-tab]')
    expect(buttons).toHaveLength(6)
    expect(buttons.map((button) => button.attributes('data-workspace-tab'))).toEqual([
      'outline',
      'timeline',
      'foreshadow',
      'character',
      'ai',
      'review'
    ])
    expect(wrapper.find('[data-workspace-tab="review"]').attributes('aria-label')).toBe('审阅')
  })

  it('toggles collapse when clicking the active tab and expands for an inactive tab', async () => {
    const wrapper = mount(RightWorkspacePanel, {
      props: {
        modelValue: 'ai'
      }
    })

    await wrapper.find('[data-workspace-tab="ai"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([''])

    await wrapper.find('[data-workspace-tab="review"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[1]).toEqual(['review'])
  })

  it('guards dirty tab switching through save and discard branches', async () => {
    const wrapper = mount(RightWorkspacePanel, {
      props: {
        modelValue: 'outline',
        dirtyTabs: ['outline']
      }
    })

    await wrapper.find('[data-workspace-tab="timeline"]').trigger('click')
    expect(wrapper.find('.right-workspace-panel__dirty-guard').exists()).toBe(true)

    await wrapper.find('[data-test="workspace-dirty-save"]').trigger('click')
    expect(wrapper.emitted('save-dirty')?.[0]).toEqual(['outline'])
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['timeline'])
  })
})
