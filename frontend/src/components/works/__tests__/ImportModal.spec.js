import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
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
  it('warns when file path is empty', async () => {
    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    await wrapper.find('.primary-button').trigger('click')

    expect(ElMessage.warning).toHaveBeenCalledWith('请输入 TXT 文件路径。')
  })

  it('submits import request and emits imported', async () => {
    mockImportTxt.mockResolvedValueOnce({ id: 'work-9', title: '导入作品' })
    const wrapper = mount(ImportModal, {
      props: {
        modelValue: true
      }
    })

    await wrapper.findAll('.field-input')[0].setValue('D:\\drafts\\novel.txt')
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
