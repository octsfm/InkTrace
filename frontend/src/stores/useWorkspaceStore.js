import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workId = ref('')
  const lastOpenChapterId = ref('')
  const cursorPosition = ref(0)
  const scrollTop = ref(0)
  const hydrated = ref(false)
  const sessionUpdatedAt = ref('')
  const viewportByChapterId = ref({})

  const hasSession = computed(() => Boolean(workId.value))

  const setWorkContext = (nextWorkId) => {
    const nextId = String(nextWorkId || '')
    if (workId.value && workId.value !== nextId) {
      resetSession()
    }
    workId.value = nextId
    hydrated.value = false
  }

  const setLastOpenChapter = (chapterId) => {
    lastOpenChapterId.value = String(chapterId || '')
  }

  const setCursorPosition = (position) => {
    const value = Number(position)
    cursorPosition.value = Number.isFinite(value) && value >= 0 ? value : 0
  }

  const setScrollTop = (value) => {
    const next = Number(value)
    scrollTop.value = Number.isFinite(next) && next >= 0 ? next : 0
  }

  const resetSession = () => {
    lastOpenChapterId.value = ''
    cursorPosition.value = 0
    scrollTop.value = 0
    sessionUpdatedAt.value = ''
    viewportByChapterId.value = {}
    hydrated.value = false
  }

  const hydrateSession = (session) => {
    const payload = session && typeof session === 'object' ? session : {}
    const chapterId = String(payload.last_open_chapter_id || payload.chapter_id || '')
    const nextCursor = Number(payload.cursor_position)
    const nextScroll = Number(payload.scroll_top)
    lastOpenChapterId.value = chapterId
    setCursorPosition(nextCursor)
    setScrollTop(nextScroll)
    viewportByChapterId.value = chapterId
      ? {
          ...viewportByChapterId.value,
          [chapterId]: {
            cursorPosition: Number.isFinite(nextCursor) && nextCursor >= 0 ? nextCursor : 0,
            scrollTop: Number.isFinite(nextScroll) && nextScroll >= 0 ? nextScroll : 0
          }
        }
      : {}
    sessionUpdatedAt.value = String(payload.updated_at || '')
    hydrated.value = true
  }

  const captureViewport = ({ chapterId = '', cursorPosition: nextCursor = 0, scrollTop: nextScroll = 0 } = {}) => {
    const id = String(chapterId || '')
    if (id) {
      setLastOpenChapter(id)
    }
    setCursorPosition(nextCursor)
    setScrollTop(nextScroll)
    if (!id) {
      return
    }
    viewportByChapterId.value = {
      ...viewportByChapterId.value,
      [id]: {
        cursorPosition: cursorPosition.value,
        scrollTop: scrollTop.value
      }
    }
  }

  const getViewport = (chapterId) => {
    const id = String(chapterId || '')
    if (!id) {
      return {
        cursorPosition: 0,
        scrollTop: 0
      }
    }
    const cached = viewportByChapterId.value[id]
    if (cached) {
      return {
        cursorPosition: Number(cached.cursorPosition || 0),
        scrollTop: Number(cached.scrollTop || 0)
      }
    }
    return {
      cursorPosition: 0,
      scrollTop: 0
    }
  }

  const setViewport = (chapterId, viewport = {}) => {
    const id = String(chapterId || '')
    if (!id) return
    const nextCursor = Number(viewport.cursorPosition)
    const nextScroll = Number(viewport.scrollTop)
    viewportByChapterId.value = {
      ...viewportByChapterId.value,
      [id]: {
        cursorPosition: Number.isFinite(nextCursor) && nextCursor >= 0 ? nextCursor : 0,
        scrollTop: Number.isFinite(nextScroll) && nextScroll >= 0 ? nextScroll : 0
      }
    }
  }

  const toSessionPayload = () => ({
    chapter_id: lastOpenChapterId.value,
    cursor_position: cursorPosition.value,
    scroll_top: scrollTop.value
  })

  const markPersisted = (updatedAt = new Date().toISOString()) => {
    sessionUpdatedAt.value = String(updatedAt || '')
    hydrated.value = true
  }

  const clearAll = () => {
    workId.value = ''
    resetSession()
  }

  return {
    workId,
    lastOpenChapterId,
    cursorPosition,
    scrollTop,
    hydrated,
    sessionUpdatedAt,
    viewportByChapterId,
    hasSession,
    setWorkContext,
    setLastOpenChapter,
    setCursorPosition,
    setScrollTop,
    resetSession,
    hydrateSession,
    captureViewport,
    getViewport,
    setViewport,
    toSessionPayload,
    markPersisted,
    clearAll
  }
})
