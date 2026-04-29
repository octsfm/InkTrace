import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

import ImportModal from '../ImportModal.vue'

const mockImportTxt = vi.fn()

vi.mock('@/api', () => ({
  v1IOApi: {
    importTxt: (...args) => mockImportTxt(...args)
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() }
}))

describe('ImportModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    delete window.electronAPI
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

  it('fills readonly input after selecting file in electron', async () => {
    const selectFile = vi.fn().mockResolvedValue({
      canceled: false,
      filePaths: ['D:\\drafts\\novel.txt']
    })
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        selectFile
      }
    })

    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    await wrapper.find('.select-button').trigger('click')
    await flushPromises()

    expect(selectFile).toHaveBeenCalled()
    expect(wrapper.find('.field-input').element.value).toBe('novel.txt')
  })

  it('submits import request and emits imported', async () => {
    mockImportTxt.mockResolvedValueOnce({ id: 'work-9', title: '导入作品' })
    const selectFile = vi.fn().mockResolvedValue({
      canceled: false,
      filePaths: ['D:\\drafts\\novel.txt']
    })
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: {
        selectFile
      }
    })
    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    await wrapper.find('.select-button').trigger('click')
    await flushPromises()
    await wrapper.findAll('.field-input')[1].setValue('导入作品')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(mockImportTxt).toHaveBeenCalledWith({
      file_path: 'D:\\drafts\\novel.txt',
      title: '导入作品',
      author: ''
    })
    expect(wrapper.emitted('imported')).toEqual([[{ id: 'work-9', title: '导入作品' }]])
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]])
    expect(ElMessage.success).toHaveBeenCalledWith('TXT 导入成功')
  })
})
