import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import VersionConflictModal from '../VersionConflictModal.vue'

describe('VersionConflictModal', () => {
  it('renders conflict copy when opened', () => {
    const wrapper = mount(VersionConflictModal, {
      props: {
        modelValue: true,
        description: '第2章在服务端已存在更新版本，请先决定是否覆盖。'
      }
    })

    expect(wrapper.text()).toContain('检测到版本冲突')
    expect(wrapper.text()).toContain('第2章在服务端已存在更新版本，请先决定是否覆盖。')
    expect(wrapper.text()).toContain('处理前，本地草稿会继续保留')
  })

  it('provides a local vs server compare entry', () => {
    const wrapper = mount(VersionConflictModal, {
      props: {
        modelValue: true,
        localContent: 'local draft',
        serverContent: 'server content'
      }
    })

    expect(wrapper.find('.compare-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('查看本地版本 vs 服务端版本')
    expect(wrapper.text()).toContain('本地版本')
    expect(wrapper.text()).toContain('local draft')
    expect(wrapper.text()).toContain('服务端版本')
    expect(wrapper.text()).toContain('server content')
  })

  it('emits explicit cancel discard and override actions', async () => {
    const wrapper = mount(VersionConflictModal, {
      props: { modelValue: true }
    })

    await wrapper.find('button.ghost-button').trigger('click')
    await wrapper.findAll('button.ghost-button')[1].trigger('click')
    await wrapper.find('button.danger-button').trigger('click')

    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('discard')).toHaveLength(1)
    expect(wrapper.emitted('override')).toHaveLength(1)
  })

  it('does not render when closed', () => {
    const wrapper = mount(VersionConflictModal, {
      props: { modelValue: false }
    })

    expect(wrapper.find('.modal-mask').exists()).toBe(false)
  })
})
