import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SelectionRewriteToolbar from '../SelectionRewriteToolbar.vue'

describe('SelectionRewriteToolbar', () => {
  it('renders six rewrite mode actions and emits selected mode', async () => {
    const wrapper = mount(SelectionRewriteToolbar, {
      props: {
        visible: true
      }
    })

    expect(wrapper.findAll('button')).toHaveLength(6)
    expect(wrapper.text()).toContain('扩写')
    expect(wrapper.text()).toContain('重写')
    expect(wrapper.text()).toContain('缩写')
    expect(wrapper.text()).toContain('润色')
    expect(wrapper.text()).toContain('对白优化')
    expect(wrapper.text()).toContain('降低 AI 味')

    await wrapper.get('[data-test="selection-rewrite-mode-polish"]').trigger('click')

    expect(wrapper.emitted('mode-select')).toEqual([['polish']])
  })

  it('stays hidden when selection does not satisfy visibility conditions', () => {
    const wrapper = mount(SelectionRewriteToolbar, {
      props: {
        visible: false
      }
    })

    expect(wrapper.find('[data-test="selection-rewrite-toolbar"]').exists()).toBe(false)
  })
})
