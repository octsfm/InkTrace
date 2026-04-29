import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

import ImportModal from '../ImportModal.vue'

const mockImportTxtUpload = vi.fn()

vi.mock('@/api', () => ({
  v1IOApi: {
    importTxtUpload: (...args) => mockImportTxtUpload(...args)
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() }
}))

describe('ImportModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('warns when no file is selected', async () => {
    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    await wrapper.find('.primary-button').trigger('click')

    expect(ElMessage.warning).toHaveBeenCalledWith('请先选择 TXT 文件。')
  })

  it('fills readonly input after selecting file in web upload flow', async () => {
    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    const input = wrapper.find('input[type="file"]')
    const file = new File(['第一章 起点\n这里是正文。'], 'novel.txt', { type: 'text/plain' })
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [file]
    })
    await input.trigger('change')

    expect(wrapper.find('.field-input').element.value).toBe('novel.txt')
  })

  it('submits import request and emits imported', async () => {
    mockImportTxtUpload.mockResolvedValueOnce({ id: 'work-9', title: '导入作品' })
    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    const input = wrapper.find('input[type="file"]')
    const file = new File(['第一章 起点\n这里是正文。'], 'novel.txt', { type: 'text/plain' })
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [file]
    })
    await input.trigger('change')
    await wrapper.findAll('.field-input')[1].setValue('导入作品')
    await wrapper.findAll('.field-input')[2].setValue('作者甲')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(mockImportTxtUpload).toHaveBeenCalledWith({
      txtFile: file,
      title: '导入作品',
      author: '作者甲'
    })
    expect(wrapper.emitted('imported')).toEqual([[{ id: 'work-9', title: '导入作品' }]])
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]])
    expect(ElMessage.success).toHaveBeenCalledWith('TXT 导入成功')
  })
})
