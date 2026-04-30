const LOG_CATEGORIES = new Set(['draft', 'flush', 'conflict', 'offline'])
const SENSITIVE_KEYS = new Set([
  'content',
  'draft',
  'payload',
  'contentText',
  'contentTreeJson',
  'description',
  'aliases',
])

function isDebugEnabled() {
  return import.meta.env.DEV && import.meta.env.VITE_WORKBENCH_DEBUG === 'true'
}

function sanitizeMeta(meta = {}) {
  return Object.fromEntries(
    Object.entries(meta).filter(([key]) => !SENSITIVE_KEYS.has(key))
  )
}

export function logWorkbenchDebug(category, event, meta = {}) {
  if (!isDebugEnabled()) return
  if (!LOG_CATEGORIES.has(category)) return

  console.debug(`[Workbench:${category}] ${event}`, sanitizeMeta(meta))
}

export const workbenchLogCategories = Object.freeze([...LOG_CATEGORIES])
