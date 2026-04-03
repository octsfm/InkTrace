import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import NovelWrite from '../NovelWrite.vue'

const mockNovelGet = vi.fn()
const mockGetByNovel = vi.fn()
const mockListBranchesV2 = vi.fn()
const mockBranchesV2 = vi.fn()
const mockChapterPlanV2 = vi.fn()
const mockWritePreviewV2 = vi.fn()
const mockWriteCommitV2 = vi.fn()
const mockContinuationContextV2 = vi.fn()
const mockMemoryViewV2 = vi.fn()
const mockActivePlotArcsV2 = vi.fn()
const mockRouterPush = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'novel_1' },
    query: {}
  }),
  useRouter: () => ({ push: mockRouterPush })
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
    listBranchesV2: (...args) => mockListBranchesV2(...args),
    branchesV2: (...args) => mockBranchesV2(...args),
    chapterPlanV2: (...args) => mockChapterPlanV2(...args),
    writePreviewV2: (...args) => mockWritePreviewV2(...args),
    writeCommitV2: (...args) => mockWriteCommitV2(...args),
    continuationContextV2: (...args) => mockContinuationContextV2(...args),
    memoryViewV2: (...args) => mockMemoryViewV2(...args),
    activePlotArcsV2: (...args) => mockActivePlotArcsV2(...args),
    refreshMemoryV2: vi.fn()
  }
}))

const mountPage = async () => {
  const slotStub = { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' }
  const wrapper = mount(NovelWrite, {
    global: {
      stubs: {
        'el-button': {
          template: '<button @click="$emit(\'click\')"><slot /></button>'
        },
        'el-page-header': slotStub,
        'el-input': slotStub,
        'el-select': slotStub,
        'el-option': slotStub,
        'el-input-number': slotStub,
        'el-switch': slotStub,
        'el-form': slotStub,
        'el-form-item': slotStub,
        'el-card': slotStub,
        'el-row': slotStub,
        'el-col': slotStub,
        'el-alert': slotStub,
        'el-radio': slotStub,
        'el-radio-group': slotStub,
        'el-tag': slotStub,
        'el-table': slotStub,
        'el-table-column': slotStub,
        'el-descriptions': slotStub,
        'el-descriptions-item': slotStub,
        'el-tabs': slotStub,
        'el-tab-pane': slotStub,
        'el-timeline': slotStub,
        'el-timeline-item': slotStub,
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
      directives: {
        loading: () => {}
      }
    }
  })
  await flushPromises()
  return wrapper
}

describe('NovelWrite 分支交互', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    mockNovelGet.mockResolvedValue({
      id: 'novel_1',
      chapter_count: 2,
      chapters: [
        { id: 'c1', number: 1, title: '第一章', content: '甲', word_count: 1 },
        { id: 'c2', number: 2, title: '第二章', content: '乙', word_count: 1 }
      ]
    })
    mockGetByNovel.mockResolvedValue({ id: 'project_1' })
    mockListBranchesV2.mockResolvedValue({ branches: [] })
    mockBranchesV2.mockResolvedValue({
      branches: [
        { id: 'b1', title: '分支一', summary: '摘要一' },
        { id: 'b2', title: '分支二', summary: '摘要二' },
        { id: 'b3', title: '分支三', summary: '摘要三' },
        { id: 'b4', title: '分支四', summary: '摘要四' }
      ]
    })
    mockMemoryViewV2.mockResolvedValue({})
    mockActivePlotArcsV2.mockResolvedValue({ plot_arcs: [] })
    mockChapterPlanV2.mockResolvedValue({
      plans: [
        {
          id: 'plan_1',
          chapter_number: 3,
          title: '第三章 追踪',
          goal: '继续追踪',
          ending_hook: '线索升级',
          chapter_task_seed: { chapter_function: 'advance_investigation' }
        }
      ]
    })
    mockWritePreviewV2.mockResolvedValue({
      chapter_task: { chapter_function: 'advance_investigation', goals: ['追踪线索'] },
      structural_draft: { title: '第三章 追踪', content: '主角继续追踪线索。' },
      detemplated_draft: { title: '第三章 追踪', content: '主角沿着线索追了下去。' },
      integrity_check: { risk_notes: ['保持推进'], title_alignment_ok: true, progression_integrity_ok: true },
      used_structural_fallback: false
    })
    mockContinuationContextV2.mockResolvedValue({
      last_chapter_tail: '上一章结尾',
      recent_chapter_memories: []
    })
    mockWriteCommitV2.mockResolvedValue({
      generated_chapters: [
        { chapter_id: 'c3', chapter_number: 3, title: '第三章 追踪', content: '第三章正文', structural_draft: { title: '第三章 追踪', content: '第三章结构稿' }, detemplated_draft: { title: '第三章 追踪', content: '第三章改写稿' }, integrity_check: { risk_notes: [] }, used_structural_fallback: false },
        { chapter_id: 'c4', chapter_number: 4, title: '第四章 对峙', content: '第四章正文', structural_draft: { title: '第四章 对峙', content: '第四章结构稿' }, detemplated_draft: { title: '第四章 对峙', content: '第四章改写稿' }, integrity_check: { risk_notes: [] }, used_structural_fallback: false }
      ],
      latest_chapter: { chapter_id: 'c4', chapter_number: 4, title: '第四章 对峙' },
      latest_structural_draft: { title: '第四章 对峙', content: '第四章结构稿' },
      latest_detemplated_draft: { title: '第四章 对峙', content: '第四章改写稿' },
      latest_draft_integrity_check: { risk_notes: [] },
      used_structural_fallback: false,
      chapter_saved: true,
      memory_refreshed: true,
      saved_chapter_ids: ['c3', 'c4'],
      memory_view: { main_plot: '主线已推进' }
    })
  })

  it('进入页面不自动生成分支', async () => {
    await mountPage()
    expect(mockNovelGet).toHaveBeenCalled()
    expect(mockBranchesV2).not.toHaveBeenCalled()
  })

  it('进入页面会恢复后端已保存分支', async () => {
    mockListBranchesV2.mockResolvedValueOnce({
      branches: [
        { id: 'b1', title: '分支一', summary: '摘要一' }
      ]
    })
    window.localStorage.setItem('inktrace:selected-branch:project_1', 'b1')
    await mountPage()
    expect(mockListBranchesV2).toHaveBeenCalledWith('project_1')
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

  it('预览区展示标题正文而不是 JSON 字符串', async () => {
    const wrapper = await mountPage()
    wrapper.vm.state.selectedBranchId = 'b1'
    const buttons = wrapper.findAll('button')

    await buttons.find((node) => node.text().includes('生成章节计划')).trigger('click')
    await flushPromises()
    await buttons.find((node) => node.text().includes('预览一章')).trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('第三章 追踪')
    expect(text).toContain('主角继续追踪线索。')
    expect(text).not.toContain('"title":')
    expect(text).not.toContain('"content":')
  })

  it('提交后展示本次生成的完整章节列表', async () => {
    const wrapper = await mountPage()
    wrapper.vm.state.selectedBranchId = 'b1'
    const buttons = wrapper.findAll('button')

    await buttons.find((node) => node.text().includes('生成章节计划')).trigger('click')
    await flushPromises()
    await buttons.find((node) => node.text().includes('保存并继续生成')).trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('共 2 章')
    expect(text).toContain('第三章 追踪')
    expect(text).toContain('第四章 对峙')
    expect(mockWriteCommitV2).toHaveBeenCalledWith('project_1', expect.objectContaining({ plan_ids: ['plan_1'] }))
  })
})
