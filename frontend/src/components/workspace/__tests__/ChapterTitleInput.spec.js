import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ChapterTitleInput from '../ChapterTitleInput.vue'

describe('ChapterTitleInput', () => {
  it('separates order prefix from the editable title field', () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: 'Storm',
        orderIndex: 3
      }
    })

    expect(wrapper.find('.chapter-title-prefix').text()).toBe('第3章')
    expect(wrapper.find('input').element.value).toBe('Storm')
  })

  it('displays only chapter prefix when title is empty', () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: '',
        orderIndex: 5
      }
    })

    expect(wrapper.find('.chapter-title-prefix').text()).toBe('第5章')
    expect(wrapper.find('input').element.value).toBe('')
  })

  it('emits only the raw user title input', async () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: 'Old',
        orderIndex: 2
      }
    })

    await wrapper.find('input').setValue('New Title')

    expect(wrapper.emitted('update:modelValue')).toEqual([['New Title']])
  })

  it('emits empty string when user clears the title', async () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: 'Old',
        orderIndex: 2
      }
    })

    await wrapper.find('input').setValue('')

    expect(wrapper.emitted('update:modelValue')).toEqual([['']])
  })
})
