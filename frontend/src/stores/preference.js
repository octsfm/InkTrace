import { defineStore } from 'pinia'

const STORAGE_KEY = 'inktrace.preference.v1'
const DEFAULT_FONT_FAMILY = 'system-ui'
const DEFAULT_FONT_SIZE = 18
const DEFAULT_LINE_HEIGHT = 1.8
const DEFAULT_THEME = 'light'
const ALLOWED_THEMES = new Set(['light', 'warm', 'dark'])

const applyGlobalTheme = (theme) => {
  if (typeof document === 'undefined') return
  const normalized = ALLOWED_THEMES.has(String(theme || '').trim())
    ? String(theme).trim()
    : DEFAULT_THEME
  document.documentElement.setAttribute('data-app-theme', normalized)
}

const buildTodayKey = (date = new Date()) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const clampNumber = (value, fallback, min, max) => {
  const next = Number(value)
  if (!Number.isFinite(next)) return fallback
  return Math.min(max, Math.max(min, next))
}

const normalizeState = (payload = {}) => {
  const todayKey = typeof payload.todayKey === 'string' && payload.todayKey.trim()
    ? payload.todayKey.trim()
    : buildTodayKey()

  const normalizedAppTheme = ALLOWED_THEMES.has(String(payload.appTheme || payload.theme || '').trim())
    ? String(payload.appTheme || payload.theme).trim()
    : DEFAULT_THEME

  return {
    focusMode: Boolean(payload.focusMode),
    fontFamily: String(payload.fontFamily || DEFAULT_FONT_FAMILY).trim() || DEFAULT_FONT_FAMILY,
    fontSize: clampNumber(payload.fontSize, DEFAULT_FONT_SIZE, 12, 32),
    lineHeight: clampNumber(payload.lineHeight, DEFAULT_LINE_HEIGHT, 1.2, 2.4),
    appTheme: normalizedAppTheme,
    // Editor theme follows app theme to keep a single visible theme concept.
    editorTheme: normalizedAppTheme,
    todayWordDelta: Math.max(0, Math.floor(Number(payload.todayWordDelta) || 0)),
    todayKey
  }
}

const defaultState = () => normalizeState()

const readPersistedState = () => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return defaultState()
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState()
    return normalizeState(JSON.parse(raw))
  } catch {
    return defaultState()
  }
}

const persistState = (state) => {
  if (typeof window === 'undefined' || !window.localStorage) return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
    focusMode: Boolean(state.focusMode),
    fontFamily: String(state.fontFamily || DEFAULT_FONT_FAMILY),
    fontSize: Number(state.fontSize || DEFAULT_FONT_SIZE),
    lineHeight: Number(state.lineHeight || DEFAULT_LINE_HEIGHT),
    appTheme: String(state.appTheme || DEFAULT_THEME),
    editorTheme: String(state.editorTheme || DEFAULT_THEME),
    todayWordDelta: Math.max(0, Math.floor(Number(state.todayWordDelta) || 0)),
    todayKey: String(state.todayKey || buildTodayKey())
  }))
  applyGlobalTheme(state.appTheme)
}

export const usePreferenceStore = defineStore('workbenchPreference', {
  state: () => readPersistedState(),
  getters: {
    editorPreferences: (state) => ({
      fontFamily: state.fontFamily,
      fontSize: state.fontSize,
      lineHeight: state.lineHeight,
      theme: state.editorTheme
    })
  },
  actions: {
    persist() {
      persistState(this.$state)
    },
    syncTodayKey(now = new Date()) {
      const nextKey = buildTodayKey(now)
      if (this.todayKey === nextKey) return this.todayKey
      this.todayKey = nextKey
      this.todayWordDelta = 0
      this.persist()
      return this.todayKey
    },
    setFocusMode(enabled) {
      this.focusMode = Boolean(enabled)
      this.persist()
    },
    toggleFocusMode() {
      this.setFocusMode(!this.focusMode)
    },
    updateWritingPreferences(patch = {}) {
      let appThemeChanged = false
      if (Object.prototype.hasOwnProperty.call(patch, 'fontFamily')) {
        this.fontFamily = String(patch.fontFamily || DEFAULT_FONT_FAMILY).trim() || DEFAULT_FONT_FAMILY
      }
      if (Object.prototype.hasOwnProperty.call(patch, 'fontSize')) {
        this.fontSize = clampNumber(patch.fontSize, this.fontSize, 12, 32)
      }
      if (Object.prototype.hasOwnProperty.call(patch, 'lineHeight')) {
        this.lineHeight = clampNumber(patch.lineHeight, this.lineHeight, 1.2, 2.4)
      }
      if (Object.prototype.hasOwnProperty.call(patch, 'appTheme')) {
        const nextTheme = String(patch.appTheme || '').trim()
        this.appTheme = ALLOWED_THEMES.has(nextTheme) ? nextTheme : DEFAULT_THEME
        appThemeChanged = true
      }
      // editorTheme is no longer user-facing; keep backward compatibility for old calls.
      if (Object.prototype.hasOwnProperty.call(patch, 'editorTheme') && !appThemeChanged) {
        const nextTheme = String(patch.editorTheme || '').trim()
        this.appTheme = ALLOWED_THEMES.has(nextTheme) ? nextTheme : DEFAULT_THEME
        appThemeChanged = true
      }
      if (Object.prototype.hasOwnProperty.call(patch, 'theme')) {
        const nextTheme = String(patch.theme || '').trim()
        this.appTheme = ALLOWED_THEMES.has(nextTheme) ? nextTheme : DEFAULT_THEME
        appThemeChanged = true
      }
      if (appThemeChanged) {
        this.editorTheme = this.appTheme
      }
      this.persist()
    },
    setTodayWordDelta(value, now = new Date()) {
      this.syncTodayKey(now)
      this.todayWordDelta = Math.max(0, Math.floor(Number(value) || 0))
      this.persist()
    },
    incrementTodayWordDelta(delta, now = new Date()) {
      this.syncTodayKey(now)
      this.todayWordDelta = Math.max(0, this.todayWordDelta + Math.floor(Number(delta) || 0))
      this.persist()
    },
    hydrate() {
      this.$patch(readPersistedState())
      applyGlobalTheme(this.appTheme)
      this.syncTodayKey()
    },
    reset() {
      this.$patch(defaultState())
      this.persist()
    }
  }
})

export {
  STORAGE_KEY as PREFERENCE_STORAGE_KEY,
  buildTodayKey as buildPreferenceTodayKey
}

// Ensure theme is applied even before store instance hydrate is called in a view.
applyGlobalTheme(readPersistedState().appTheme)
