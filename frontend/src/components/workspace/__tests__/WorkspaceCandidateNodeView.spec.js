import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import WorkspaceCandidateNodeView from '../WorkspaceCandidateNodeView.vue'

vi.mock('@tiptap/vue-3', () => ({
  NodeViewWrapper: { template: '<div class="mock-node-view-wrapper"><slot /></div>' }
}))

describe('WorkspaceCandidateNodeView', () => {
  it('routes actions through extension options', async () => {
    const onAction = vi.fn()
    const wrapper = mount(WorkspaceCandidateNodeView, {
      props: {
        node: {
          attrs: {
            resultLabel: '候选稿',
            title: '行内候选块 · 第一章',
            hint: '选区级候选',
            description: '围绕选中文本生成',
            resultText: '这是候选内容',
            candidateIndex: 2,
            candidateTotal: 4
          }
        },
        extension: {
          options: {
            onAction
          }
        }
      }
    })

    const applyButton = wrapper.findAll('button').find((node) => node.text().includes('采纳并插入'))
    await applyButton.trigger('click')

    expect(onAction).toHaveBeenCalledWith('apply-structural-append', expect.objectContaining({
      title: '行内候选块 · 第一章'
    }))
    expect(wrapper.text()).toContain('候选 2 / 4')
  })
})
