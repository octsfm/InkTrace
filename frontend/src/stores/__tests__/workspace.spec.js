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
})
