import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'

import {
  buildPreferenceTodayKey,
  PREFERENCE_STORAGE_KEY,
  usePreferenceStore
} from '../preference'

describe('usePreferenceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
  })

  it('persists focus mode and writing preferences locally', () => {
    const store = usePreferenceStore()

    store.setFocusMode(true)
    store.updateWritingPreferences({
      fontFamily: 'Serif',
      fontSize: 22,
      lineHeight: 2,
      theme: 'dark'
    })

    const persisted = JSON.parse(window.localStorage.getItem(PREFERENCE_STORAGE_KEY) || '{}')
    expect(persisted).toMatchObject({
      focusMode: true,
      fontFamily: 'Serif',
      fontSize: 22,
      lineHeight: 2,
      theme: 'dark'
    })
  })

  it('hydrates persisted preferences on refresh', () => {
    window.localStorage.setItem(PREFERENCE_STORAGE_KEY, JSON.stringify({
      focusMode: true,
      fontFamily: 'Monospace',
      fontSize: 20,
      lineHeight: 1.9,
      theme: 'warm',
      todayWordDelta: 128,
      todayKey: '2026-05-06'
    }))

    const store = usePreferenceStore()

    expect(store.focusMode).toBe(true)
    expect(store.fontFamily).toBe('Monospace')
    expect(store.fontSize).toBe(20)
    expect(store.lineHeight).toBe(1.9)
    expect(store.theme).toBe('warm')
    expect(store.todayWordDelta).toBe(128)
    expect(store.todayKey).toBe('2026-05-06')
  })

  it('resets to defaults and persists them', () => {
    const store = usePreferenceStore()
    store.setFocusMode(true)
    store.updateWritingPreferences({
      fontFamily: 'Serif',
      fontSize: 24,
      lineHeight: 2.1,
      theme: 'dark'
    })
    store.setTodayWordDelta(300, new Date('2026-05-06T08:00:00'))

    store.reset()

    expect(store.focusMode).toBe(false)
    expect(store.fontFamily).toBe('system-ui')
    expect(store.fontSize).toBe(18)
    expect(store.lineHeight).toBe(1.8)
    expect(store.theme).toBe('light')
    expect(store.todayWordDelta).toBe(0)
    expect(store.todayKey).toBe(buildPreferenceTodayKey())
  })

  it('rolls today key forward and prevents negative today delta', () => {
    const store = usePreferenceStore()

    store.setTodayWordDelta(120, new Date('2026-05-06T08:00:00'))
    store.incrementTodayWordDelta(-999, new Date('2026-05-06T10:00:00'))
    expect(store.todayWordDelta).toBe(0)

    store.incrementTodayWordDelta(80, new Date('2026-05-07T09:00:00'))
    expect(store.todayKey).toBe('2026-05-07')
    expect(store.todayWordDelta).toBe(80)
  })

  it('restores today word delta after refresh from local persistence', () => {
    const store = usePreferenceStore()

    store.setTodayWordDelta(256, new Date('2026-05-06T08:00:00'))
    store.updateWritingPreferences({ theme: 'dark' })

    setActivePinia(createPinia())
    const refreshedStore = usePreferenceStore()

    expect(refreshedStore.todayKey).toBe('2026-05-06')
    expect(refreshedStore.todayWordDelta).toBe(256)
    expect(refreshedStore.theme).toBe('dark')
  })

  it('does not import backend api modules', () => {
    const source = readFileSync('D:/Work/InkTrace/ink-trace/frontend/src/stores/preference.js', 'utf-8')

    expect(source).not.toContain("from '@/api'")
    expect(source).not.toContain("from '../api'")
    expect(source).not.toContain('axios')
    expect(source).not.toContain('fetch(')
  })
})
