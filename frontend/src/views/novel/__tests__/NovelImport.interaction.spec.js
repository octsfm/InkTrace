import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NovelImport from '../NovelImport.vue'

const mockOrganizeProgress = vi.fn()
const mockPauseOrganize = vi.fn()
const mockResumeOrganize = vi.fn()
const mockCancelOrganize = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() })
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() }
}))

vi.mock('@/api', () => ({
  novelApi: {
    importTxt: vi.fn().mockResolvedValue({ novel_id: 'novel_1', project_id: 'project_1' })
  },
  contentApi: {
    startOrganize: vi.fn().mockResolvedValue({}),
    pauseOrganize: (...args) => mockPauseOrganize(...args),
    resumeOrganize: (...args) => mockResumeOrganize(...args),
    cancelOrganize: (...args) => mockCancelOrganize(...args),
    retryOrganize: vi.fn().mockResolvedValue({}),
    organizeProgress: (...args) => mockOrganizeProgress(...args)
  },
  projectApi: {}
}))

const slotStub = { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' }

async function mountPage() {
  const wrapper = mount(NovelImport, {
    global: {
      stubs: {
        'el-page-header': slotStub,
        'el-alert': slotStub,
        'el-form': slotStub,
        'el-form-item': slotStub,
        'el-input': slotStub,
        'el-input-number': slotStub,
        'el-select': slotStub,
        'el-option': slotStub,
        'el-switch': slotStub,
        'el-card': slotStub,
        'el-progress': slotStub,
        'el-steps': slotStub,
        'el-step': slotStub,
        'el-radio-group': slotStub,
        'el-radio': slotStub,
        'el-table': slotStub,
        'el-table-column': slotStub,
        'el-upload': slotStub,
        'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
      }
    }
  })
  await flushPromises()
  return wrapper
}

describe('NovelImport 整理进度与控制', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockOrganizeProgress.mockResolvedValue({
      status: 'paused',
      stage: 'paused',
      current: 2,
      total: 5,
      percent: 40,
      current_chapter_title: '第二章',
      message: '整理任务已暂停'
    })
    mockPauseOrganize.mockResolvedValue({})
    mockResumeOrganize.mockResolvedValue({})
    mockCancelOrganize.mockResolvedValue({})
  })

  it('展示真实整理进度与暂停继续取消按钮', async () => {
    const wrapper = await mountPage()
    wrapper.vm.createdNovelId = 'novel_1'
    await wrapper.vm.fetchOrganizeProgress()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('整理任务已暂停')
    expect(text).toContain('状态：已暂停')
    expect(text).toContain('阶段：paused')
    expect(text).toContain('暂停整理')
    expect(text).toContain('继续整理')
    expect(text).toContain('取消整理')
  })

  it('点击按钮会触发暂停继续取消接口', async () => {
    const wrapper = await mountPage()
    wrapper.vm.createdNovelId = 'novel_1'
    await wrapper.vm.fetchOrganizeProgress()
    await wrapper.vm.pauseOrganize()
    await wrapper.vm.resumeOrganize()
    await wrapper.vm.cancelOrganize()
    await flushPromises()

    expect(mockPauseOrganize).toHaveBeenCalledWith('novel_1')
    expect(mockResumeOrganize).toHaveBeenCalledWith('novel_1')
    expect(mockCancelOrganize).toHaveBeenCalledWith('novel_1')
  })
})
