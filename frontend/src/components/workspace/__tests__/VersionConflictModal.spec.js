import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import VersionConflictModal from '../VersionConflictModal.vue'

describe('VersionConflictModal', () => {
  it('renders conflict copy when opened', () => {
    const wrapper = mount(VersionConflictModal, {
      props: {
        modelValue: true,
        description: '第二章在云端已存在更新版本，请先决定是否覆盖。'
      }
    })

    expect(wrapper.text()).toContain('检测到版本冲突')
    expect(wrapper.text()).toContain('第二章在云端已存在更新版本，请先决定是否覆盖。')
    expect(wrapper.text()).toContain('如果继续保存，将会覆盖云端的最新内容。')
  })

  it('emits explicit actions instead of passive close', async () => {
    const wrapper = mount(VersionConflictModal, {
      props: {
        modelValue: true
      }
    })

    await wrapper.find('button.ghost-button').trigger('click')
    await wrapper.find('button.danger-button').trigger('click')

    expect(wrapper.emitted('discard')).toHaveLength(1)
    expect(wrapper.emitted('override')).toHaveLength(1)
  })
})
