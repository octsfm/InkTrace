import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SelectionRewriteDiffModal from '../SelectionRewriteDiffModal.vue'

describe('SelectionRewriteDiffModal', () => {
  it('renders source, rewritten result and metadata when opened', () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上',
        diffSummary: '补强环境描写',
        wordCountBefore: 8,
        wordCountAfter: 11,
        modeLabel: '润色'
      }
    })

    expect(wrapper.text()).toContain('改写结果预览')
    expect(wrapper.text()).toContain('月光落在窗台上')
    expect(wrapper.text()).toContain('月光静静落在旧窗台上')
    expect(wrapper.text()).toContain('补强环境描写')
    expect(wrapper.text()).toContain('字数：8 -> 11')
    expect(wrapper.text()).toContain('模式：润色')
  })

  it('supports edit-before-accept flow and emits edited text updates', async () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上'
      }
    })

    await wrapper.get('[data-test="selection-rewrite-edit"]').trigger('click')
    const textarea = wrapper.get('[data-test="selection-rewrite-edit-input"]')
    await textarea.setValue('月光静静落在旧窗台与书桌之间')
    await wrapper.get('[data-test="selection-rewrite-confirm-edit"]').trigger('click')

    expect(wrapper.emitted('update:editedText')?.at(-1)).toEqual(['月光静静落在旧窗台与书桌之间'])
    expect(wrapper.emitted('accept')).toEqual([[{
      finalText: '月光静静落在旧窗台与书桌之间',
      edited: true
    }]])
  })

  it('emits reject when user discards rewrite candidate', async () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上'
      }
    })

    await wrapper.get('[data-test="selection-rewrite-reject"]').trigger('click')

    expect(wrapper.emitted('reject')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]])
  })

  it('shows applying state and disables modal actions while applying rewrite', () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上',
        applying: true
      }
    })

    expect(wrapper.text()).toContain('正在应用…')
    for (const button of wrapper.findAll('button')) {
      expect(button.attributes('disabled')).toBeDefined()
    }
  })

  it('shows waiting-user-action banner and highlights accept action in pending state', () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上',
        waitingUserAction: true
      }
    })

    expect(wrapper.text()).toContain('等待你确认')
    expect(wrapper.get('[data-test="selection-rewrite-accept"]').classes()).toContain('selection-rewrite-modal__action--primary')
  })

  it('uses fullscreen panel container for diff review', () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上'
      }
    })

    expect(wrapper.get('.selection-rewrite-modal__panel').classes()).toContain('selection-rewrite-modal__panel--fullscreen')
  })

  it('shows conflicted banner and emits reselect or dismiss actions', async () => {
    const wrapper = mount(SelectionRewriteDiffModal, {
      props: {
        modelValue: true,
        sourceText: '月光落在窗台上',
        editedText: '月光静静落在旧窗台上',
        conflicted: true,
        conflictMessage: '原文已变化，请重新选择。'
      }
    })

    expect(wrapper.text()).toContain('原文已变化，请重新选择。')
    expect(wrapper.find('[data-test="selection-rewrite-accept"]').exists()).toBe(false)

    await wrapper.get('[data-test="selection-rewrite-conflict-reselect"]').trigger('click')
    await wrapper.get('[data-test="selection-rewrite-conflict-cancel"]').trigger('click')

    expect(wrapper.emitted('reselect')).toEqual([[]])
    expect(wrapper.emitted('dismiss-conflict')).toEqual([[]])
  })
})
