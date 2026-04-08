import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestingPinia } from '@pinia/testing'
import WorkspaceWritingStudio from '../WorkspaceWritingStudio.vue'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ query: { chapterId: '1' } })),
  useRouter: vi.fn(() => ({ push: vi.fn() }))
}))

// Mock TipTap
vi.mock('@tiptap/vue-3', () => ({
  EditorContent: { template: '<div class="mock-editor-content"></div>' },
  useEditor: vi.fn(() => ({
    value: {
      commands: { setContent: vi.fn() },
      getText: vi.fn(() => 'test content'),
      destroy: vi.fn()
    }
  }))
}))

// Mock composable
vi.mock('@/composables/useWorkspaceContext', () => ({
  useWorkspaceContext: vi.fn(() => ({
    state: {
      editor: {
        chapter: { id: '1', title: 'Chapter 1', content: 'test content' },
        loading: false,
        saving: false,
        aiRunning: false,
        dirty: false,
        chapterTask: {},
        chapterArcs: [],
        contextMeta: {},
        integrityCheck: null
      },
      projectId: 'proj-1',
      markEditorDirty: vi.fn()
    },
    currentChapterId: { value: '1' },
    loadEditorChapter: vi.fn(),
    saveEditorChapter: vi.fn(),
    runEditorAiAction: vi.fn(),
    openSection: vi.fn()
  }))
}))

describe('WorkspaceWritingStudio.vue', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(WorkspaceWritingStudio, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            workspace: {
              activeView: 'writing',
              isZenMode: false
            }
          },
          createSpy: vi.fn,
        })],
        stubs: ['el-button', 'el-skeleton', 'el-empty', 'el-icon', 'el-tooltip'],
        mocks: {
          $route: { query: { chapterId: '1' } },
          $router: { push: vi.fn() }
        }
      }
    })
  })

  it('renders the editor surface without side context cards', () => {
    expect(wrapper.find('.editor-surface').exists()).toBe(true)
    
    // According to the new UI spec, side cards like context-column should be removed from the center area
    expect(wrapper.find('.context-column').exists()).toBe(false)
  })

  it('renders a clean top bar and title input', () => {
    expect(wrapper.find('.chapter-title-input').exists()).toBe(true)
  })
})
