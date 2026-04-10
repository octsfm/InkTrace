import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NovelList from '../NovelList.vue'

const mockPush = vi.fn()
const mockList = vi.fn()
const mockGetByNovel = vi.fn()
const mockChapterTasksV2 = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush })
}))

vi.mock('@/api', () => ({
  novelApi: {
    list: (...args) => mockList(...args),
    delete: vi.fn()
  },
  projectApi: {
    getByNovel: (...args) => mockGetByNovel(...args),
    chapterTasksV2: (...args) => mockChapterTasksV2(...args)
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
  ElMessageBox: { confirm: vi.fn() }
}))

const slotStub = { template: '<div><slot /></div>' }

const mountPage = async () => {
  const wrapper = mount(NovelList, {
    global: {
      stubs: {
        'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
        'el-tag': slotStub,
        'el-progress': slotStub,
        'el-empty': slotStub,
        'el-skeleton': slotStub,
        'el-icon': slotStub,
        Edit: slotStub,
        Plus: slotStub,
        Delete: slotStub
      },
      mocks: {
        $router: { push: mockPush }
      }
    }
  })
  await flushPromises()
  return wrapper
}

describe('NovelList Dashboard 入口', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockList.mockResolvedValue([
      {
        id: 'novel-1',
        title: '风暴将至',
        author: '测试作者',
        genre: 'xuanhuan',
        status: 'active',
        chapter_count: 12,
        current_word_count: 32000,
        target_word_count: 120000,
        updated_at: '2026-04-09T10:00:00.000Z'
      }
    ])
    mockGetByNovel.mockResolvedValue({ id: 'project-1' })
    mockChapterTasksV2.mockResolvedValue([
      { id: 'task-1', status: 'failed', task_type: 'audit' }
    ])
  })

  it('shows featured workspace entry for the most recent novel', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('继续最近工作台')
    expect(wrapper.text()).toContain('最近工作区')
    expect(wrapper.text()).toContain('处理失败任务')
    expect(wrapper.text()).toContain('失败任务')
    expect(wrapper.text()).toContain('高优先级')
    expect(wrapper.text()).toContain('Overview')
    expect(wrapper.text()).toContain('Structure')
    expect(wrapper.text()).toContain('Chapters')
    expect(wrapper.text()).toContain('Tasks')
    expect(wrapper.text()).toContain('1 个失败任务')
  })

  it('navigates to workspace structure section from featured actions', async () => {
    const wrapper = await mountPage()
    const structureButton = wrapper.findAll('button').find((node) => node.text().includes('Structure'))
    expect(structureButton).toBeTruthy()
    await structureButton.trigger('click')
    expect(mockPush).toHaveBeenCalledWith({
      path: '/novel/novel-1',
      query: { section: 'structure' }
    })
  })

  it('navigates to workspace tasks section from featured actions', async () => {
    const wrapper = await mountPage()
    const tasksButton = wrapper.findAll('button').find((node) => node.text().includes('Tasks'))
    expect(tasksButton).toBeTruthy()
    await tasksButton.trigger('click')
    expect(mockPush).toHaveBeenCalledWith({
      path: '/novel/novel-1',
      query: { section: 'tasks' }
    })
  })

  it('navigates to tasks from failed-task shortcut', async () => {
    const wrapper = await mountPage()
    const failedButton = wrapper.findAll('button').find((node) => node.text().includes('处理失败任务'))
    expect(failedButton).toBeTruthy()
    await failedButton.trigger('click')
    expect(mockPush).toHaveBeenCalledWith({
      path: '/novel/novel-1',
      query: { section: 'tasks' }
    })
  })
})
