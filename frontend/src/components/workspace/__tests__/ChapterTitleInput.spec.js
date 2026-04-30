import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ChapterTitleInput from '../ChapterTitleInput.vue'

describe('ChapterTitleInput', () => {
  it('displays order prefix and user title without duplicating storage prefix', () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: 'Storm',
        orderIndex: 3
      }
    })

    expect(wrapper.find('input').element.value).toBe('第3章 Storm')
  })

  it('displays only chapter prefix when title is empty', () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: '',
        orderIndex: 5
      }
    })

    expect(wrapper.find('input').element.value).toBe('第5章')
  })

  it('emits only user title and strips a chapter prefix from input', async () => {
    const wrapper = mount(ChapterTitleInput, {
      props: {
        modelValue: 'Old',
        orderIndex: 2
      }
    })

    await wrapper.find('input').setValue('第2章 New Title')

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
