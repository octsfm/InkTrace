import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { v1SessionsApi, v1WorksApi } from '@/api'

export const useWorkspaceStore = defineStore('workspace', () => {
  const work = ref(null)
  const session = ref(null)
  const workId = ref('')
  const lastOpenChapterId = ref('')
  const cursorPosition = ref(0)
  const scrollTop = ref(0)
  const hydrated = ref(false)
  const sessionUpdatedAt = ref('')
  const viewportByChapterId = ref({})
  const loading = ref(false)
  const error = ref('')

  const hasSession = computed(() => Boolean(workId.value))

  const normalizeNonNegativeInt = (value) => {
    const next = Number(value)
    if (!Number.isFinite(next) || next < 0) {
      return 0
    }
    return Math.round(next)
  }

  const setWorkContext = (nextWorkId) => {
    const nextId = String(nextWorkId || '')
    if (workId.value && workId.value !== nextId) {
      resetSession()
      work.value = null
      session.value = null
    }
    workId.value = nextId
    hydrated.value = false
  }

  const setWork = (payload) => {
    work.value = payload && typeof payload === 'object' ? { ...payload } : null
    if (work.value?.id) {
      workId.value = String(work.value.id)
    }
  }

  const setLastOpenChapter = (chapterId) => {
    lastOpenChapterId.value = String(chapterId || '')
  }

  const setCursorPosition = (position) => {
    cursorPosition.value = normalizeNonNegativeInt(position)
  }

  const setScrollTop = (value) => {
    scrollTop.value = normalizeNonNegativeInt(value)
  }

  const resetSession = () => {
    lastOpenChapterId.value = ''
    cursorPosition.value = 0
    scrollTop.value = 0
    sessionUpdatedAt.value = ''
    viewportByChapterId.value = {}
    hydrated.value = false
  }

  const hydrateSession = (sessionPayload) => {
    const payload = sessionPayload && typeof sessionPayload === 'object' ? sessionPayload : {}
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
            cursorPosition: normalizeNonNegativeInt(nextCursor),
            scrollTop: normalizeNonNegativeInt(nextScroll)
          }
        }
      : {}
    sessionUpdatedAt.value = String(payload.updated_at || '')
    session.value = { ...payload }
    hydrated.value = true
  }

  const initializeWorkspace = async (nextWorkId) => {
    const id = String(nextWorkId || '')
    setWorkContext(id)
    loading.value = true
    error.value = ''
    try {
      const workPayload = await v1WorksApi.get(id)
      setWork(workPayload)
      let sessionPayload = null
      try {
        sessionPayload = await v1SessionsApi.get(id)
      } catch (sessionError) {
        resetSession()
      }
      hydrateSession(sessionPayload)
      return {
        work: work.value,
        session: session.value
      }
    } catch (err) {
      error.value = String(err?.response?.data?.detail || err?.message || 'workspace_init_failed')
      hydrated.value = false
      throw err
    } finally {
      loading.value = false
    }
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
        cursorPosition: normalizeNonNegativeInt(cached.cursorPosition),
        scrollTop: normalizeNonNegativeInt(cached.scrollTop)
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
        cursorPosition: normalizeNonNegativeInt(nextCursor),
        scrollTop: normalizeNonNegativeInt(nextScroll)
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

  const saveSessionPosition = async ({
    chapterId = '',
    activeChapterId = '',
    cursorPosition: nextCursor = cursorPosition.value,
    scrollTop: nextScroll = scrollTop.value
  } = {}) => {
    const targetChapterId = String(activeChapterId || chapterId || lastOpenChapterId.value || '')
    captureViewport({
      chapterId: targetChapterId,
      cursorPosition: nextCursor,
      scrollTop: nextScroll
    })
    if (!workId.value) {
      return null
    }
    const payload = {
      active_chapter_id: targetChapterId,
      cursor_position: cursorPosition.value,
      scroll_top: scrollTop.value
    }
    const savedSession = await v1SessionsApi.save(workId.value, payload)
    hydrateSession(savedSession)
    markPersisted(savedSession?.updated_at)
    return session.value
  }

  const clearAll = () => {
    work.value = null
    session.value = null
    loading.value = false
    error.value = ''
    workId.value = ''
    resetSession()
  }

  return {
    work,
    session,
    workId,
    lastOpenChapterId,
    cursorPosition,
    scrollTop,
    hydrated,
    sessionUpdatedAt,
    viewportByChapterId,
    loading,
    error,
    hasSession,
    setWorkContext,
    setWork,
    setLastOpenChapter,
    setCursorPosition,
    setScrollTop,
    resetSession,
    hydrateSession,
    initializeWorkspace,
    captureViewport,
    getViewport,
    setViewport,
    toSessionPayload,
    markPersisted,
    saveSessionPosition,
    clearAll
  }
})
