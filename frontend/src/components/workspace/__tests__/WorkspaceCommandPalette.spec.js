import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WorkspaceCommandPalette from '../WorkspaceCommandPalette.vue'

describe('WorkspaceCommandPalette.vue', () => {
  const items = [
    {
      id: 'view-writing',
      group: '视图',
      title: '打开写作',
      subtitle: '进入正文写作工作区',
      action: { type: 'section', section: 'writing' }
    },
    {
      id: 'chapter-1',
      group: '章节',
      title: '第一章',
      subtitle: '打开章节写作',
      action: { type: 'chapter', chapterId: 'chapter-1' }
    }
  ]

  it('renders command items when visible', () => {
    const wrapper = mount(WorkspaceCommandPalette, {
      props: {
        visible: true,
        query: '',
        groupedItems: [
          { group: '视图', items }
        ]
      }
    })

    expect(wrapper.text()).toContain('打开写作')
    expect(wrapper.text()).toContain('第一章')
  })

  it('emits execute for selected item when pressing enter', async () => {
    const wrapper = mount(WorkspaceCommandPalette, {
      props: {
        visible: true,
        query: '',
        groupedItems: [
          { group: '视图', items }
        ]
      }
    })

    await wrapper.find('.palette-input').trigger('keydown.enter')
    expect(wrapper.emitted('execute')).toBeTruthy()
    expect(wrapper.emitted('execute')[0][0]).toEqual(items[0])
  })

  it('renders recent command section when query is empty', () => {
    const wrapper = mount(WorkspaceCommandPalette, {
      props: {
        visible: true,
        query: '',
        groupedItems: [
          {
            group: '最近命令',
            items: [
              {
                id: 'recent-writing',
                group: '视图',
                title: '最近打开写作',
                subtitle: '最近执行过的命令',
                action: { type: 'section', section: 'writing' }
              }
            ]
          },
          {
            group: '视图',
            items
          }
        ]
      }
    })

    expect(wrapper.text()).toContain('最近命令')
    expect(wrapper.text()).toContain('最近打开写作')
  })

  it('prioritizes recent object group before recent commands when query is empty', () => {
    const wrapper = mount(WorkspaceCommandPalette, {
      props: {
        visible: true,
        query: '',
        groupedItems: [
          {
            group: '最近对象',
            items: [
              {
                id: 'recent-object-chapter',
                group: '最近对象',
                title: '第一章',
                subtitle: '重新打开该章节 · 刚刚',
                action: { type: 'chapter', chapterId: 'chapter-1' }
              }
            ]
          },
          {
            group: '最近命令',
            items: [
              {
                id: 'recent-writing',
                group: '视图',
                title: '最近打开写作',
                subtitle: '最近执行过的命令',
                action: { type: 'section', section: 'writing' }
              }
            ]
          },
          {
            group: '视图',
            items
          }
        ]
      }
    })

    const titles = wrapper.findAll('.group-title')
    expect(titles[0].text()).toBe('最近对象')
    expect(titles[1].text()).toBe('最近命令')
  })
})
