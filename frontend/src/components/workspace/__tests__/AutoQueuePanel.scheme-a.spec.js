import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AutoQueuePanel from '../AutoQueuePanel.vue'


describe('AutoQueuePanel scheme A', () => {
  it('presents a plain-language continue-writing entrance', () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        chapterId: 'chapter_001',
        targetChapters: 3
      }
    })

    expect(wrapper.text()).toContain('接着写')
    expect(wrapper.text()).toContain('下一章，你最想看到什么？')
    expect(wrapper.text()).toContain('让冲突更紧张')
    expect(wrapper.text()).toContain('让人物关系推进')
    expect(wrapper.text()).toContain('把刚才的伏笔接下去')
    expect(wrapper.text()).toContain('只会写一份新稿，不会改动你的正文')
    expect(wrapper.text()).toContain('写一章给我看')
    expect(wrapper.text()).toContain('不用补充，直接接着写')
    expect(wrapper.text()).toContain('更多保护设置')
    expect(wrapper.find('[data-test="auto-queue-mode-continuous"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('自动续写队列')
    expect(wrapper.text()).not.toContain('令牌')
  })

  it('turns a preset into editable final writing intent', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: {
        featureEnabled: true,
        chapterId: 'chapter_001',
        targetChapters: 3
      }
    })

    await wrapper.get('[data-test="auto-queue-intent-conflict"]').trigger('click')

    const textarea = wrapper.get('[data-test="auto-queue-writing-intent"]')
    expect(textarea.element.value).toBe('下一章优先增强当前冲突，让局势更紧张，但不要提前解决核心矛盾。')
    expect(wrapper.emitted('update:writing-intent')?.at(-1)).toEqual([
      '下一章优先增强当前冲突，让局势更紧张，但不要提前解决核心矛盾。'
    ])
    expect(textarea.attributes('maxlength')).toBe('60')
  })

  it('starts directly with an empty intent when the author skips the prompt', async () => {
    const wrapper = mount(AutoQueuePanel, {
      props: { featureEnabled: true, chapterId: 'chapter_001', targetChapters: 3 }
    })

    await wrapper.get('[data-test="auto-queue-start-direct"]').trigger('click')

    expect(wrapper.emitted('update:writing-intent')?.at(-1)).toEqual([''])
    expect(wrapper.emitted('start')).toHaveLength(1)
  })
})
