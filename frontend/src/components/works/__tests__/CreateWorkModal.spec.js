import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

import CreateWorkModal from '../CreateWorkModal.vue'

const mockCreate = vi.fn()

vi.mock('@/api', () => ({
  v1WorksApi: {
    create: (...args) => mockCreate(...args)
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() }
}))

describe('CreateWorkModal', () => {
  it('prefills default title and blocks empty title submit', async () => {
    const wrapper = mount(CreateWorkModal, {
      props: {
        modelValue: true,
        defaultTitle: '未命名作品 0429'
      }
    })

    expect(wrapper.find('.field-input').element.value).toBe('未命名作品 0429')
    await wrapper.find('.field-input').setValue('   ')
    await wrapper.find('.primary-button').trigger('click')

    expect(ElMessage.warning).toHaveBeenCalledWith('请输入作品标题')
    expect(mockCreate).not.toHaveBeenCalled()
  })

  it('creates work and emits created', async () => {
    mockCreate.mockResolvedValueOnce({ id: 'work-9', title: '风暴将至', author: '测试作者' })
    const wrapper = mount(CreateWorkModal, {
      props: {
        modelValue: true,
        defaultTitle: '未命名作品 0429'
      }
    })

    const inputs = wrapper.findAll('.field-input')
    await inputs[0].setValue('风暴将至')
    await inputs[1].setValue('测试作者')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(mockCreate).toHaveBeenCalledWith({
      title: '风暴将至',
      author: '测试作者'
    })
    expect(wrapper.emitted('created')).toEqual([[{ id: 'work-9', title: '风暴将至', author: '测试作者' }]])
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]])
    expect(ElMessage.success).toHaveBeenCalledWith('已创建新作品')
  })
})
