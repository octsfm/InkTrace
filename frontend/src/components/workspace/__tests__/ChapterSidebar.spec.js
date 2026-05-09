﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ChapterSidebar from '../ChapterSidebar.vue'

const baseChapters = [
  { id: 'ch-1', title: 'Start', content: 'alpha', word_count: 1200, order_index: 1 },
  { id: 'ch-2', title: '', content: 'beta', word_count: 1600, order_index: 2 },
  { id: 'ch-3', title: 'Turn', content: 'gamma', word_count: 1800, order_index: 3 }
]

describe('ChapterSidebar', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('renders chapter list and active state by order_index', () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-2'
      }
    })

    expect(wrapper.text()).toContain('章节列表')
    expect(wrapper.text()).toContain('3 章')
    expect(wrapper.text()).toContain('第1章 Start')
    expect(wrapper.text()).toContain('第2章')
    expect(wrapper.text()).toContain('1,600 字')
    expect(wrapper.findAll('.chapter-item.active')).toHaveLength(1)
  })

  it('emits select and clears filters before create', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.find('.chapter-select-button').trigger('click')
    await wrapper.findAll('.sidebar-tool-input')[0].setValue('Turn')
    await wrapper.findAll('.sidebar-tool-input')[1].setValue('3')
    await wrapper.find('.add-button').trigger('click')

    expect(wrapper.emitted('select')).toEqual([['ch-1']])
    expect(wrapper.emitted('create')).toEqual([[]])
    expect(wrapper.findAll('.sidebar-tool-input')[0].element.value).toBe('')
    expect(wrapper.findAll('.sidebar-tool-input')[1].element.value).toBe('')
  })

  it('emits rename when inline editing is submitted', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1'
      },
      attachTo: document.body
    })

    await wrapper.find('.chapter-action-button').trigger('click')
    const input = wrapper.find('.chapter-rename-input')
    await input.setValue('Start Revised')
    await input.trigger('blur')

    expect(wrapper.emitted('rename')).toEqual([[{ chapterId: 'ch-1', title: 'Start Revised' }]])
  })

  it('emits delete for the target chapter', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.find('.chapter-action-button.danger').trigger('click')

    expect(wrapper.emitted('delete')).toEqual([['ch-1']])
  })

  it('emits reordered chapter ids after drag and drop', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-2'
      }
    })

    const items = wrapper.findAll('.chapter-item')
    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: 'move'
    }

    await items[2].trigger('dragstart', { dataTransfer })
    await items[0].trigger('dragover', { preventDefault: vi.fn() })
    await items[0].trigger('drop')

    expect(wrapper.emitted('reorder')).toEqual([[['ch-3', 'ch-1', 'ch-2']]])
  })

  it('filters chapters by search keyword without changing source order', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.findAll('.sidebar-tool-input')[0].setValue('Turn')

    expect(wrapper.findAll('.chapter-item')).toHaveLength(1)
    expect(wrapper.text()).toContain('第3章 Turn')
    expect(wrapper.text()).not.toContain('第1章 Start')
    expect(wrapper.props('chapters').map((item) => item.id)).toEqual(['ch-1', 'ch-2', 'ch-3'])
  })

  it('jumps to chapter by order index and emits invalid event on bad input', async () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.findAll('.sidebar-tool-input')[1].setValue('3')
    await wrapper.find('.jump-form').trigger('submit')
    expect(wrapper.emitted('select')?.at(-1)).toEqual(['ch-3'])
    expect(wrapper.findAll('.sidebar-tool-input')[1].element.value).toBe('')

    await wrapper.findAll('.sidebar-tool-input')[1].setValue('99')
    await wrapper.find('.jump-form').trigger('submit')
    expect(wrapper.emitted('jump-invalid')).toHaveLength(1)
  })

  it('renders lightweight draft and conflict markers', () => {
    const wrapper = mount(ChapterSidebar, {
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1',
        draftChapterIds: ['ch-1'],
        conflictChapterId: 'ch-3'
      }
    })

    const markers = wrapper.findAll('.chapter-state-marker')
    expect(markers).toHaveLength(2)
    expect(markers[0].attributes('data-state')).toBe('draft')
    expect(markers[0].text()).toBe('•')
    expect(markers[1].attributes('data-state')).toBe('conflict')
    expect(markers[1].text()).toBe('!')
  })

  it('scrolls active chapter into view after active id changes', async () => {
    const wrapper = mount(ChapterSidebar, {
      attachTo: document.body,
      props: {
        chapters: baseChapters,
        activeChapterId: 'ch-1'
      }
    })

    await wrapper.setProps({ activeChapterId: 'ch-3' })
    await wrapper.vm.$nextTick()

    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ block: 'nearest', behavior: 'smooth' })
  })
})
