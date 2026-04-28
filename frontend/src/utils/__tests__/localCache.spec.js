import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { localCache, SOFT_LIMIT_BYTES } from '../localCache'

describe('localCache', () => {
  let originalLocalStorage

  beforeEach(() => {
    originalLocalStorage = window.localStorage
  })

  afterEach(() => {
    localCache.clear()
    Object.defineProperty(window, 'localStorage', {
      value: originalLocalStorage,
      configurable: true
    })
  })

  it('stores and reads cached values', () => {
    localCache.set('draft:1', { content: 'hello' })

    expect(localCache.get('draft:1')).toEqual({ content: 'hello' })
    expect(localCache.keys()).toEqual(['draft:1'])
  })

  it('prunes oldest entries when soft limit is exceeded', () => {
    const quota = Math.floor(SOFT_LIMIT_BYTES / 2)
    const data = new Map()
    const currentSize = () => Array.from(data.values()).reduce((sum, item) => sum + item.length, 0)
    const fakeStorage = {
      getItem(key) {
        return data.has(key) ? data.get(key) : null
      },
      setItem(key, value) {
        const text = String(value)
        const previous = data.get(key) || ''
        const nextSize = currentSize() - previous.length + text.length
        if (nextSize > quota) {
          const error = new Error('quota exceeded')
          error.name = 'QuotaExceededError'
          throw error
        }
        data.set(key, text)
      },
      removeItem(key) {
        data.delete(key)
      }
    }
    Object.defineProperty(window, 'localStorage', {
      value: fakeStorage,
      configurable: true
    })
    const chunk = 'x'.repeat(Math.floor(quota / 3))
    localCache.set('draft:old', { content: chunk })
    localCache.set('draft:newer', { content: chunk })
    localCache.set('draft:newest', { content: chunk })

    const snapshot = localCache.debugSnapshot()

    expect(snapshot.totalSize).toBeLessThanOrEqual(SOFT_LIMIT_BYTES)
    expect(localCache.get('draft:newest')).not.toBeNull()
    expect(localCache.get('draft:old')).toBeNull()
  })
})
