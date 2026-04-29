import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'

import NovelList from '../NovelList.vue'

const mockPush = vi.fn()
const mockList = vi.fn()
const mockCreate = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush })
}))

vi.mock('@/api', () => ({
  v1WorksApi: {
    list: (...args) => mockList(...args),
    create: (...args) => mockCreate(...args)
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
}))

const slotStub = { template: '<div><slot /></div>' }

const mountPage = async () => {
  const wrapper = mount(NovelList, {
    global: {
      stubs: {
        ImportModal: {
          props: ['modelValue'],
          emits: ['update:modelValue', 'imported'],
          template: '<div v-if="modelValue" class="import-modal-stub">import modal</div>'
        },
        'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
        'el-empty': slotStub,
        'el-skeleton': slotStub,
        'el-icon': slotStub,
        Plus: slotStub,
        Upload: slotStub
      },
      mocks: {
        $router: { push: mockPush }
      }
    }
  })
  await flushPromises()
  return wrapper
}

describe('NovelList WorksList 页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockList.mockResolvedValue({
      items: [
        {
          id: 'work-1',
          title: '风暴将至',
          author: '测试作者',
          current_word_count: 32000,
          updated_at: '2026-04-09T10:00:00.000Z'
        }
      ],
      total: 1
    })
    mockCreate.mockResolvedValue({
      id: 'work-new',
      title: '未命名作品 0428',
      author: '',
      current_word_count: 0,
      updated_at: '2026-04-28T10:00:00.000Z'
    })
  })

  it('renders hero actions and work list', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('书架')
    expect(wrapper.text()).toContain('新建作品')
    expect(wrapper.text()).toContain('导入 TXT')
    expect(wrapper.text()).toContain('我的作品')
    expect(wrapper.text()).toContain('风暴将至')
    expect(wrapper.text()).toContain('32,000')
  })

  it('creates a new work and opens workspace', async () => {
    const wrapper = await mountPage()
    const createButton = wrapper.findAll('button').find((node) => node.text().includes('新建作品'))
    expect(createButton).toBeTruthy()
    await createButton.trigger('click')
    await flushPromises()

    expect(mockCreate).toHaveBeenCalledTimes(1)
    expect(ElMessage.success).toHaveBeenCalledWith('已创建新作品')
    expect(mockPush).toHaveBeenCalledWith({ path: '/works/work-new' })
  })

  it('opens import modal', async () => {
    const wrapper = await mountPage()
    const importButton = wrapper.findAll('button').find((node) => node.text().includes('导入 TXT'))
    expect(importButton).toBeTruthy()
    await importButton.trigger('click')

    expect(wrapper.find('.import-modal-stub').exists()).toBe(true)
  })

  it('opens workspace when clicking a work card', async () => {
    const wrapper = await mountPage()
    const card = wrapper.find('.work-card-shell')
    expect(card.exists()).toBe(true)
    await card.trigger('click')

    expect(mockPush).toHaveBeenCalledWith({ path: '/works/work-1' })
  })

  it('shows empty onboarding when no works exist', async () => {
    mockList.mockResolvedValueOnce({ items: [], total: 0 })
    const wrapper = await mountPage()

    expect(wrapper.text()).toContain('你可以先新建空白作品')
  })

  it('shows error state and retries loading', async () => {
    mockList
      .mockRejectedValueOnce(new Error('backend down'))
      .mockResolvedValueOnce({ items: [], total: 0 })

    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('书架加载失败')
    expect(wrapper.text()).toContain('暂时无法读取作品列表')

    const retryButton = wrapper.findAll('button').find((node) => node.text().includes('重新加载'))
    expect(retryButton).toBeTruthy()
    const callCountBeforeRetry = mockList.mock.calls.length
    await retryButton.trigger('click')
    await flushPromises()

    expect(mockList.mock.calls.length).toBeGreaterThan(callCountBeforeRetry)
  })
})
