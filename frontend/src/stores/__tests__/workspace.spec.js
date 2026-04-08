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
    expect(store.activeView).toBe('overview') // Default view is usually overview or writing
    expect(store.activeChapterId).toBeNull()
    expect(store.isZenMode).toBe(false)
  })

  it('should switch view and handle zen mode rules', () => {
    const store = useWorkspaceStore()
    
    // Switch view
    store.switchView('structure')
    expect(store.activeView).toBe('structure')
    
    // Test that zen mode is disabled when switching to a non-writing view
    store.isZenMode = true
    store.switchView('tasks')
    expect(store.isZenMode).toBe(false)
  })

  it('should open chapter and automatically switch to writing view', () => {
    const store = useWorkspaceStore()
    
    store.activeView = 'overview'
    store.openChapter('chapter-1')
    
    expect(store.activeChapterId).toBe('chapter-1')
    expect(store.activeView).toBe('writing')
    expect(store.isZenMode).toBe(false) // Opening a chapter should exit zen mode to show context
  })
})
