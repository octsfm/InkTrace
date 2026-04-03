import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NovelDetail from '../NovelDetail.vue'
import { formatChapterStatus } from '@/constants/display'

const mockNovelGet = vi.fn()
const mockGetByNovel = vi.fn()
const mockMemoryView = vi.fn()
const mockOrganizeProgress = vi.fn()
const mockPauseOrganize = vi.fn()
const mockResumeOrganize = vi.fn()
const mockCancelOrganize = vi.fn()
const mockActivePlotArcsV2 = vi.fn()
const mockRouterPush = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'novel_1' } }),
  useRouter: () => ({ push: mockRouterPush })
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), info: vi.fn() },
  ElMessageBox: { confirm: vi.fn().mockResolvedValue() }
}))

vi.mock('@/api', () => ({
  novelApi: {
    get: (...args) => mockNovelGet(...args),
    deleteChapter: vi.fn()
  },
  projectApi: {
    getByNovel: (...args) => mockGetByNovel(...args),
    memoryViewV2: (...args) => mockMemoryView(...args),
    activePlotArcsV2: (...args) => mockActivePlotArcsV2(...args),
    listBranchesV2: vi.fn().mockResolvedValue({ branches: [] }),
    branchesV2: vi.fn().mockResolvedValue({ branches: [] })
  },
  contentApi: {
    organizeProgress: (...args) => mockOrganizeProgress(...args),
    pauseOrganize: (...args) => mockPauseOrganize(...args),
    resumeOrganize: (...args) => mockResumeOrganize(...args),
    cancelOrganize: (...args) => mockCancelOrganize(...args)
  },
  exportApi: {
    export: vi.fn(),
    download: vi.fn()
  }
}))

const slotStub = { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' }

async function mountPage() {
  const wrapper = mount(NovelDetail, {
    global: {
      stubs: {
        'el-page-header': slotStub,
        'el-alert': slotStub,
        'el-row': slotStub,
        'el-col': slotStub,
        'el-card': slotStub,
        'el-descriptions': slotStub,
        'el-descriptions-item': slotStub,
        'el-progress': slotStub,
        'el-radio-group': slotStub,
        'el-radio': slotStub,
        'el-radio-button': slotStub,
        'el-table': slotStub,
        'el-table-column': { template: '<div />' },
        'el-pagination': slotStub,
        'el-dialog': slotStub,
        'el-form': slotStub,
        'el-form-item': slotStub,
        'el-input': slotStub,
        'el-select': slotStub,
        'el-option': slotStub,
        'el-empty': slotStub,
        'el-collapse': slotStub,
        'el-collapse-item': slotStub,
        'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' }
      },
      directives: { loading: () => {} }
    }
  })
  await flushPromises()
  return wrapper
}

describe('NovelDetail 展示与整理进度', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNovelGet.mockResolvedValue({
      id: 'novel_1',
      title: '测试小说',
      author: '作者',
      genre: 'xuanhuan',
      status: 'active',
      chapters: [{ id: 'c1', number: 1, title: '第一章', status: 'saved', updated_at: '2026-01-01' }]
    })
    mockGetByNovel.mockResolvedValue({ id: 'project_1' })
    mockMemoryView.mockResolvedValue({})
    mockOrganizeProgress.mockResolvedValue({ status: 'running', stage: 'chapter_analysis', current: 1, total: 3, percent: 33, current_chapter_title: '第一章', message: '正在分析' })
    mockPauseOrganize.mockResolvedValue({})
    mockResumeOrganize.mockResolvedValue({})
    mockCancelOrganize.mockResolvedValue({})
    mockActivePlotArcsV2.mockResolvedValue({ plot_arcs: [] })
  })

  it('显示中文题材状态与整理进度', async () => {
    const wrapper = await mountPage()
    const text = wrapper.text()
    expect(text).toContain('玄幻')
    expect(text).toContain('进行中')
    expect(formatChapterStatus('saved')).toBe('已保存')
    expect(text).toContain('正在分析')
    expect(text).toContain('暂停')
    expect(text).toContain('继续')
  })

  it('触发暂停继续取消接口', async () => {
    const wrapper = await mountPage()
    await wrapper.vm.pauseOrganize()
    await wrapper.vm.resumeOrganize()
    await wrapper.vm.cancelOrganize()
    await flushPromises()

    expect(mockPauseOrganize).toHaveBeenCalledWith('novel_1')
    expect(mockResumeOrganize).toHaveBeenCalledWith('novel_1')
    expect(mockCancelOrganize).toHaveBeenCalledWith('novel_1')
  })

  it('整理完成后只刷新一次详情数据，不递归重载页面', async () => {
    mockOrganizeProgress.mockResolvedValue({ status: 'done', stage: 'done', current: 3, total: 3, percent: 100, current_chapter_title: '第三章', message: '整理完成' })

    await mountPage()

    expect(mockNovelGet).toHaveBeenCalledTimes(2)
    expect(mockGetByNovel).toHaveBeenCalledTimes(1)
    expect(mockMemoryView).toHaveBeenCalledTimes(2)
    expect(mockOrganizeProgress).toHaveBeenCalledTimes(1)
  })

  it('根据活跃剧情弧展示作者助手建议并携带参数跳转', async () => {
    mockOrganizeProgress.mockResolvedValue({ status: 'done', stage: 'done', current: 3, total: 3, percent: 100, current_chapter_title: '第三章', message: '整理完成' })
    mockActivePlotArcsV2.mockResolvedValue({
      plot_arcs: [
        {
          arc_id: 'arc_main',
          title: '主线危机',
          arc_type: 'main_arc',
          priority: 'core',
          current_stage: 'crisis',
          next_push_suggestion: '下一章必须升级危机'
        }
      ]
    })

    const wrapper = await mountPage()
    const text = wrapper.text()
    expect(text).toContain('作者助手建议')
    expect(text).toContain('主线危机')
    expect(text).toContain('重规划')

    await wrapper.vm.goToWriteWithAssistant()
    expect(mockRouterPush).toHaveBeenCalledWith({
      path: '/novel/novel_1/write',
      query: { targetArcId: 'arc_main', planningMode: 'deep_planning' }
    })
  })
})
