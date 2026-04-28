import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import PureTextEditor from '../PureTextEditor.vue'

describe('PureTextEditor', () => {
  let originalRequestAnimationFrame

  beforeEach(() => {
    originalRequestAnimationFrame = globalThis.requestAnimationFrame
    globalThis.requestAnimationFrame = vi.fn((callback) => {
      callback()
      return 1
    })
  })

  afterEach(() => {
    globalThis.requestAnimationFrame = originalRequestAnimationFrame
  })

  it('renders chapter title and word count', () => {
    const wrapper = mount(PureTextEditor, {
      props: {
        modelValue: '春风十里',
        chapterTitle: '第一章'
      }
    })

    expect(wrapper.text()).toContain('第一章')
    expect(wrapper.text()).toContain('本章字数 4')
  })

  it('counts effective characters only', () => {
    const wrapper = mount(PureTextEditor, {
      props: {
        modelValue: ' \n\t春 风 '
      }
    })

    expect(wrapper.text()).toContain('本章字数 2')
  })

  it('emits updated content and cursor position on input', async () => {
    const wrapper = mount(PureTextEditor, {
      props: {
        modelValue: '旧内容'
      }
    })

    const textarea = wrapper.find('textarea')
    textarea.element.selectionStart = 3
    await textarea.setValue('新内容')

    expect(wrapper.emitted('update:modelValue')).toEqual([['新内容']])
    expect(wrapper.emitted('cursor-change')).toEqual([[{ cursorPosition: 3 }]])
  })

  it('pastes plain text only and updates cursor state', async () => {
    const wrapper = mount(PureTextEditor, {
      props: {
        modelValue: 'HelloWorld'
      }
    })

    const textarea = wrapper.find('textarea')
    textarea.element.selectionStart = 5
    textarea.element.selectionEnd = 10
    const getData = vi.fn((type) => (type === 'text/plain' ? ' 纯文本 ' : '<b>富文本</b>'))
    const event = new Event('paste', { bubbles: true, cancelable: true })
    Object.defineProperty(event, 'clipboardData', {
      value: { getData }
    })

    textarea.element.dispatchEvent(event)
    await wrapper.vm.$nextTick()

    expect(event.defaultPrevented).toBe(true)
    expect(getData).toHaveBeenCalledWith('text/plain')
    expect(wrapper.emitted('update:modelValue')).toEqual([['Hello 纯文本 ']])
    expect(wrapper.emitted('cursor-change')).toEqual([[{ cursorPosition: 10 }]])
  })

  it('emits scroll position', async () => {
    const wrapper = mount(PureTextEditor)
    const textarea = wrapper.find('textarea')
    textarea.element.scrollTop = 128

    await textarea.trigger('scroll')

    expect(wrapper.emitted('scroll-change')).toEqual([[{ scrollTop: 128 }]])
  })

  it('restores cursor and scroll position within valid bounds', async () => {
    const wrapper = mount(PureTextEditor, {
      props: {
        modelValue: '恢复现场'
      }
    })
    const textarea = wrapper.find('textarea')
    Object.defineProperty(textarea.element, 'scrollHeight', {
      configurable: true,
      value: 260
    })
    Object.defineProperty(textarea.element, 'clientHeight', {
      configurable: true,
      value: 100
    })

    wrapper.vm.restoreViewport({
      cursorPosition: 99,
      scrollTop: 999
    })
    await wrapper.vm.$nextTick()

    expect(textarea.element.selectionStart).toBe(4)
    expect(textarea.element.selectionEnd).toBe(4)
    expect(textarea.element.scrollTop).toBe(160)
    expect(wrapper.emitted('cursor-change')?.at(-1)).toEqual([{ cursorPosition: 4 }])
    expect(wrapper.emitted('scroll-change')?.at(-1)).toEqual([{ scrollTop: 160 }])
  })

  it('shows soft limit warning after 200000 effective characters without blocking input', async () => {
    const wrapper = mount(PureTextEditor, {
      props: {
        modelValue: `${'字'.repeat(200000)} \n\t字`
      }
    })

    expect(wrapper.text()).toContain('当前章节已超过 20 万有效字符')

    const textarea = wrapper.find('textarea')
    await textarea.setValue('继续创作')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['继续创作'])
  })
})
