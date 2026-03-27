import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import NovelWrite from '../NovelWrite.vue'

const mockNovelGet = vi.fn()
const mockGetByNovel = vi.fn()
const mockBranchesV2 = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'novel_1' },
    query: {}
  })
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    warning: vi.fn(),
    info: vi.fn(),
    success: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn()
  }
}))

vi.mock('@/api', () => ({
  novelApi: {
    get: (...args) => mockNovelGet(...args),
    deleteChapter: vi.fn()
  },
  projectApi: {
    getByNovel: (...args) => mockGetByNovel(...args),
    branchesV2: (...args) => mockBranchesV2(...args),
    chapterPlanV2: vi.fn(),
    writeV2: vi.fn(),
    refreshMemoryV2: vi.fn()
  }
}))

const mountPage = async () => {
  const slotStub = { template: '<div><slot /></div>' }
  const wrapper = mount(NovelWrite, {
    global: {
      stubs: {
        'el-button': {
          template: '<button @click="$emit(\'click\')"><slot /></button>'
        },
        'el-input': slotStub,
        'el-input-number': slotStub,
        'el-switch': slotStub,
        'el-form': slotStub,
        'el-form-item': slotStub,
        'el-card': slotStub,
        'el-row': slotStub,
        'el-col': slotStub,
        'el-alert': slotStub,
        'el-radio': slotStub,
        'el-tag': slotStub,
        'el-divider': slotStub,
        'el-scrollbar': slotStub,
        'el-icon': slotStub,
        'el-collapse': slotStub,
        'el-collapse-item': slotStub,
        ArrowLeft: slotStub,
        Edit: slotStub,
        CopyDocument: slotStub,
        Download: slotStub
      },
      mocks: {
        $router: { push: vi.fn() },
        $route: { params: { id: 'novel_1' } }
      }
    }
  })
  await flushPromises()
  return wrapper
}

describe('NovelWrite 分支交互', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNovelGet.mockResolvedValue({
      id: 'novel_1',
      chapter_count: 2,
      chapters: [
        { id: 'c1', number: 1, title: '第一章', content: '甲', word_count: 1 },
        { id: 'c2', number: 2, title: '第二章', content: '乙', word_count: 1 }
      ]
    })
    mockGetByNovel.mockResolvedValue({ id: 'project_1' })
    mockBranchesV2.mockResolvedValue({
      branches: [
        { id: 'b1', title: '分支一', summary: '摘要一' },
        { id: 'b2', title: '分支二', summary: '摘要二' },
        { id: 'b3', title: '分支三', summary: '摘要三' },
        { id: 'b4', title: '分支四', summary: '摘要四' }
      ]
    })
  })

  it('进入页面不自动生成分支', async () => {
    await mountPage()
    expect(mockNovelGet).toHaveBeenCalled()
    expect(mockBranchesV2).not.toHaveBeenCalled()
  })

  it('点击生成分支按钮后才请求4个分支', async () => {
    const wrapper = await mountPage()
    mockBranchesV2.mockClear()
    const button = wrapper.findAll('button').find((node) => node.text().includes('生成分支'))
    expect(button).toBeTruthy()
    await button.trigger('click')
    await flushPromises()
    expect(mockBranchesV2).toHaveBeenCalled()
    const lastCall = mockBranchesV2.mock.calls[mockBranchesV2.mock.calls.length - 1]
    expect(lastCall[0]).toBe('project_1')
    expect(lastCall[1]).toEqual(expect.objectContaining({ branch_count: 4 }))
  })
})
