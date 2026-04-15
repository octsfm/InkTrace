import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WorkspaceInlineResultBlock from '../WorkspaceInlineResultBlock.vue'

describe('WorkspaceInlineResultBlock', () => {
  it('renders token-level highlights for diff rows', () => {
    const wrapper = mount(WorkspaceInlineResultBlock, {
      props: {
        resultType: 'diff',
        resultLabel: '改写稿',
        title: '行内改写对照',
        originalText: '主角走进房间。',
        resultText: '主角冲进房间，立刻停下。',
        actions: []
      }
    })

    expect(wrapper.findAll('.token-removed').length).toBeGreaterThan(0)
    expect(wrapper.findAll('.token-added').length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('主角')
    expect(wrapper.text()).toContain('立刻停下')
  })
})
