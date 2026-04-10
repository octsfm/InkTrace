import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach } from 'vitest'
import { useWorkspaceStore } from '../workspace'

describe('Workspace Store (DDD + TDD)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize workspace with correct default state', () => {
    const store = useWorkspaceStore()
    
    // Assert default state
    expect(store.novelId).toBeNull()
    expect(store.currentView).toBe('writing')
    expect(store.currentChapterId).toBeNull()
    expect(store.currentCopilotTab).toBe('context')
    expect(store.isZenMode).toBe(false)
  })

  it('should switch view and handle zen mode rules', () => {
    const store = useWorkspaceStore()
    
    // Switch view
    store.switchView('structure')
    expect(store.currentView).toBe('structure')
    
    // Test that zen mode is disabled when switching to a non-writing view
    store.isZenMode = true
    store.switchView('tasks')
    expect(store.isZenMode).toBe(false)
  })

  it('should open chapter and automatically switch to writing view', () => {
    const store = useWorkspaceStore()
    
    store.currentView = 'overview'
    store.openChapter('chapter-1')
    
    expect(store.currentChapterId).toBe('chapter-1')
    expect(store.currentView).toBe('writing')
    expect(store.currentObject).toEqual({
      type: 'chapter',
      id: 'chapter-1',
      title: ''
    })
    expect(store.isZenMode).toBe(false) // Opening a chapter should exit zen mode to show context
  })

  it('should persist copilot chat sessions by object and restore draft/messages on switch', () => {
    const store = useWorkspaceStore()

    store.ensureCopilotChatSession({
      key: 'writing::chapter:chapter-1',
      label: 'Chapter 1',
      view: 'writing',
      objectTitle: 'Chapter 1'
    })
    store.setActiveCopilotChatSession('writing::chapter:chapter-1')
    store.setCopilotChatDraft('请分析这一章的问题')
    store.appendCopilotChatMessage({ role: 'user', content: '请分析这一章的问题' })

    store.ensureCopilotChatSession({
      key: 'structure::arc:arc-1',
      label: '主线追踪',
      view: 'structure',
      objectTitle: '主线追踪'
    })
    store.setActiveCopilotChatSession('structure::arc:arc-1')
    expect(store.copilotChatDraft).toBe('')
    expect(store.copilotChatMessages).toEqual([])

    store.setActiveCopilotChatSession('writing::chapter:chapter-1')
    expect(store.copilotChatDraft).toBe('请分析这一章的问题')
    expect(store.copilotChatMessages).toEqual([
      { role: 'user', content: '请分析这一章的问题' }
    ])
  })

  it('should keep a readable summary for copilot chat sessions', () => {
    const store = useWorkspaceStore()

    store.ensureCopilotChatSession({
      key: 'writing::chapter:chapter-1',
      label: 'Chapter 1',
      view: 'writing',
      objectTitle: 'Chapter 1'
    })
    store.setActiveCopilotChatSession('writing::chapter:chapter-1')
    store.appendCopilotChatMessage({
      role: 'assistant',
      content: '这一章当前最需要补的是角色动机与冲突升级之间的衔接。'
    })

    expect(store.copilotChatSessions[0]).toMatchObject({
      summary: '这一章当前最需要补的是角色动机与冲突升级之间的衔接。'
    })
  })

  it('should record non-chapter objects into recent open documents', () => {
    const store = useWorkspaceStore()

    store.setCurrentObject({
      type: 'plot_arc',
      arcId: 'arc-1',
      title: '主线追踪'
    })

    expect(store.openDocuments[0]).toMatchObject({
      type: 'plot_arc',
      id: 'arc-1',
      title: '主线追踪'
    })
    expect(typeof store.openDocuments[0].lastOpenedAt).toBe('number')
  })
})
