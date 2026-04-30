const STORAGE_PREFIX = 'inktrace:v1:cache:'
const INDEX_KEY = `${STORAGE_PREFIX}index`
const SOFT_LIMIT_BYTES = 10 * 1024 * 1024

const now = () => Date.now()

const readIndex = () => {
  try {
    const raw = window.localStorage.getItem(INDEX_KEY)
    const parsed = JSON.parse(raw || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    return []
  }
}

const writeIndex = (entries) => {
  window.localStorage.setItem(INDEX_KEY, JSON.stringify(entries))
}

const storageKeyOf = (key) => `${STORAGE_PREFIX}${String(key || '').trim()}`

const estimateSize = (value) => {
  return new Blob([JSON.stringify(value)]).size
}

const getTotalSize = (entries) => {
  return entries.reduce((sum, item) => sum + Number(item?.size || 0), 0)
}

const pruneToFit = (entries, incomingSize = 0, protectedKeys = new Set()) => {
  const nextEntries = [...entries].sort((a, b) => Number(a.updatedAt || 0) - Number(b.updatedAt || 0))
  let total = getTotalSize(nextEntries)
  while (nextEntries.length && total + incomingSize > SOFT_LIMIT_BYTES) {
    const oldestIndex = nextEntries.findIndex((item) => !protectedKeys.has(item.key))
    if (oldestIndex < 0) break
    const [oldest] = nextEntries.splice(oldestIndex, 1)
    window.localStorage.removeItem(storageKeyOf(oldest.key))
    total -= Number(oldest?.size || 0)
  }
  return nextEntries
}

const pruneOldest = (entries, protectedKeys = new Set()) => {
  const nextEntries = [...entries].sort((a, b) => Number(a.updatedAt || 0) - Number(b.updatedAt || 0))
  const oldestIndex = nextEntries.findIndex((item) => !protectedKeys.has(item.key))
  if (oldestIndex < 0) return entries
  const [oldest] = nextEntries.splice(oldestIndex, 1)
  window.localStorage.removeItem(storageKeyOf(oldest.key))
  return nextEntries
}

const isQuotaExceededError = (error) => {
  const message = String(error?.message || '')
  return error?.name === 'QuotaExceededError' || message.includes('quota')
}

export const localCache = {
  set(key, value, options = {}) {
    const normalizedKey = String(key || '').trim()
    if (!normalizedKey) return

    const protectedKeys = new Set((options.protectedKeys || []).map((item) => String(item || '').trim()).filter(Boolean))
    const serializedSize = estimateSize(value)
    let index = readIndex().filter((item) => item.key !== normalizedKey)
    index = pruneToFit(index, serializedSize, protectedKeys)
    const payload = JSON.stringify(value)

    while (true) {
      try {
        window.localStorage.setItem(storageKeyOf(normalizedKey), payload)
        index.push({
          key: normalizedKey,
          size: serializedSize,
          updatedAt: now()
        })
        writeIndex(index)
        return
      } catch (error) {
        if (!isQuotaExceededError(error) || !index.length) {
          throw error
        }
        const nextIndex = pruneOldest(index, protectedKeys)
        if (nextIndex.length === index.length) {
          writeIndex(index)
          return
        }
        index = nextIndex
      }
    }
  },

  get(key, fallback = null) {
    const normalizedKey = String(key || '').trim()
    if (!normalizedKey) return fallback
    try {
      const raw = window.localStorage.getItem(storageKeyOf(normalizedKey))
      return raw == null ? fallback : JSON.parse(raw)
    } catch (error) {
      return fallback
    }
  },

  remove(key) {
    const normalizedKey = String(key || '').trim()
    if (!normalizedKey) return
    window.localStorage.removeItem(storageKeyOf(normalizedKey))
    writeIndex(readIndex().filter((item) => item.key !== normalizedKey))
  },

  clear() {
    const index = readIndex()
    index.forEach((item) => {
      window.localStorage.removeItem(storageKeyOf(item.key))
    })
    window.localStorage.removeItem(INDEX_KEY)
  },

  keys() {
    return readIndex()
      .sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0))
      .map((item) => item.key)
  },

  debugSnapshot() {
    const index = readIndex()
    return {
      keys: index.map((item) => item.key),
      totalSize: getTotalSize(index),
      limit: SOFT_LIMIT_BYTES
    }
  }
}

export { SOFT_LIMIT_BYTES }
