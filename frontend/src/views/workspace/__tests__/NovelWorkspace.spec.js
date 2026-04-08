import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestingPinia } from '@pinia/testing'
import { useWorkspaceStore } from '@/stores/workspace'
import NovelWorkspace from '../NovelWorkspace.vue'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: { id: '1' }, query: {} })),
  useRouter: vi.fn(() => ({ push: vi.fn() }))
}))

// Mock child components
vi.mock('../WorkspaceOverview.vue', () => ({ default: { name: 'WorkspaceOverview', template: '<div class="workspace-overview-mock">Overview</div>' } }))
vi.mock('../WorkspaceWritingStudio.vue', () => ({ default: { name: 'WorkspaceWritingStudio', template: '<div class="workspace-writing-mock">Writing</div>' } }))
vi.mock('../WorkspaceStructureStudio.vue', () => ({ default: { name: 'WorkspaceStructureStudio', template: '<div class="workspace-structure-mock">Structure</div>' } }))
vi.mock('../WorkspaceChapterManager.vue', () => ({ default: { name: 'WorkspaceChapterManager', template: '<div class="workspace-chapter-mock">Chapters</div>' } }))
vi.mock('../WorkspaceTasksAudit.vue', () => ({ default: { name: 'WorkspaceTasksAudit', template: '<div class="workspace-tasks-mock">Tasks</div>' } }))
vi.mock('@/components/workspace/WorkspaceSidebar.vue', () => ({ default: { name: 'WorkspaceSidebar', template: '<div class="workspace-sidebar-mock">Sidebar</div>' } }))
vi.mock('@/components/workspace/WorkspaceCopilotPanel.vue', () => ({ default: { name: 'WorkspaceCopilotPanel', template: '<div class="workspace-copilot-mock">Copilot</div>' } }))

describe('NovelWorkspace.vue', () => {
  let wrapper
  let store

  const mountComponent = () => {
    wrapper = mount(NovelWorkspace, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            workspace: {
              activeView: 'overview',
              isZenMode: false,
              isCopilotOpen: true
            }
          },
          createSpy: vi.fn,
        })],
        stubs: ['el-icon', 'el-tooltip', 'el-button', 'el-alert'],
        mocks: {
          $route: {
            params: { id: '1' }
          },
          $router: {
            push: vi.fn()
          }
        }
      }
    })
    store = useWorkspaceStore()
  }

  beforeEach(() => {
    mountComponent()
  })

  it('renders the workspace layout with default overview view', () => {
    // Should have left nav
    expect(wrapper.find('.workspace-nav-bar').exists()).toBe(true)
    
    // Should render Overview mock based on activeView
    expect(wrapper.find('.workspace-overview-mock').exists()).toBe(true)
    expect(wrapper.find('.workspace-writing-mock').exists()).toBe(false)
  })

  it('switches to writing view when store activeView changes', async () => {
    store.activeView = 'writing'
    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('.workspace-writing-mock').exists()).toBe(true)
    expect(wrapper.find('.workspace-overview-mock').exists()).toBe(false)
  })

  it('hides left nav when zen mode is enabled', async () => {
    store.activeView = 'writing'
    store.isZenMode = true
    await wrapper.vm.$nextTick()
    
    // In Vue Test Utils, elements with v-show=false still exist but are not visible
    expect(wrapper.find('.workspace-nav-bar').classes()).toContain('hidden-in-zen')
    expect(wrapper.find('.workspace-copilot-mock').isVisible()).toBe(false)
  })
})
