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

    expect(wrapper.findAll('[data-test^="selection-rewrite-mode-"]')).toHaveLength(6)
    expect(wrapper.text()).toContain('扩写')
    expect(wrapper.text()).toContain('重写')
    expect(wrapper.text()).toContain('缩写')
    expect(wrapper.text()).toContain('润色')
    expect(wrapper.text()).toContain('对白优化')
    expect(wrapper.text()).toContain('降低 AI 味')

    await wrapper.get('[data-test="selection-rewrite-mode-polish"]').trigger('click')

    expect(wrapper.emitted('mode-select')).toEqual([['polish']])
  })

  it('emits clear-history when user clicks clear history action', async () => {
    const wrapper = mount(SelectionRewriteToolbar, {
      props: {
        visible: true
      }
    })

    await wrapper.get('[data-test="selection-rewrite-clear-history"]').trigger('click')

    expect(wrapper.emitted('clear-history')).toEqual([[]])
  })

  it('shows polling hint and disables toolbar actions while rewrite is generating', () => {
    const wrapper = mount(SelectionRewriteToolbar, {
      props: {
        visible: true,
        busy: true,
        polling: true
      }
    })

    expect(wrapper.text()).toContain('正在生成，请稍等')
    for (const button of wrapper.findAll('button')) {
      expect(button.attributes('disabled')).toBeDefined()
    }
  })

  it('applies floating anchor style and below placement class', () => {
    const wrapper = mount(SelectionRewriteToolbar, {
      props: {
        visible: true,
        floatingStyle: {
          left: '180px',
          top: '96px'
        },
        placement: 'below'
      }
    })

    const toolbar = wrapper.get('[data-test="selection-rewrite-toolbar"]')
    expect(toolbar.attributes('style')).toContain('left: 180px;')
    expect(toolbar.attributes('style')).toContain('top: 96px;')
    expect(toolbar.classes()).toContain('selection-rewrite-toolbar--below')
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
