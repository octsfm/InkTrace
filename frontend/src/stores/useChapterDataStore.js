import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useChapterDataStore = defineStore('chapterData', () => {
  const chapters = ref([])
  const activeChapterId = ref('')
  const draftByChapterId = ref({})
  const draftTitleByChapterId = ref({})

  const chapterCount = computed(() => chapters.value.length)
  const activeChapter = computed(() => chapters.value.find((item) => item.id === activeChapterId.value) || null)
  const activeChapterContent = computed(() => {
    const activeId = String(activeChapterId.value || '')
    if (!activeId) return ''
    if (Object.prototype.hasOwnProperty.call(draftByChapterId.value, activeId)) {
      return String(draftByChapterId.value[activeId] || '')
    }
    return String(activeChapter.value?.content || '')
  })
  const activeChapterTitle = computed(() => {
    const activeId = String(activeChapterId.value || '')
    if (!activeId) return ''
    if (Object.prototype.hasOwnProperty.call(draftTitleByChapterId.value, activeId)) {
      return String(draftTitleByChapterId.value[activeId] || '')
    }
    return String(activeChapter.value?.title || '')
  })

  const normalizeChapter = (chapter, fallbackIndex = 0) => {
    const orderIndex = Number(chapter?.order_index)
    return {
      ...(chapter || {}),
      id: String(chapter?.id || ''),
      title: String(chapter?.title || ''),
      content: String(chapter?.content || ''),
      order_index: Number.isFinite(orderIndex) && orderIndex > 0 ? orderIndex : fallbackIndex + 1
    }
  }

  const sortByOrderIndex = (items) => [...items].sort((left, right) => {
    const leftOrder = Number(left?.order_index || 0)
    const rightOrder = Number(right?.order_index || 0)
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder
    }
    return String(left?.id || '').localeCompare(String(right?.id || ''))
  })

  const setChapters = (items) => {
    const normalized = Array.isArray(items)
      ? items.map((item, index) => normalizeChapter(item, index)).filter((item) => item.id)
      : []
    chapters.value = sortByOrderIndex(normalized)
    if (activeChapterId.value && !chapters.value.some((item) => item.id === activeChapterId.value)) {
      activeChapterId.value = ''
    }
  }

  const setActiveChapter = (chapterId) => {
    activeChapterId.value = String(chapterId || '')
  }

  const upsertChapter = (chapter) => {
    if (!chapter || !chapter.id) return
    const normalized = normalizeChapter(chapter, chapters.value.length)
    const index = chapters.value.findIndex((item) => item.id === normalized.id)
    if (index < 0) {
      chapters.value = sortByOrderIndex([...chapters.value, normalized])
      return
    }
    const next = [...chapters.value]
    next[index] = normalizeChapter({ ...next[index], ...normalized }, index)
    chapters.value = sortByOrderIndex(next)
  }

  const appendCreatedChapter = (chapter, { activate = true, clearSearch = false } = {}) => {
    upsertChapter({
      ...chapter,
      order_index: Number(chapter?.order_index || 0) > 0 ? Number(chapter.order_index) : chapters.value.length + 1
    })
    if (activate && chapter?.id) {
      activeChapterId.value = String(chapter.id)
    }
    return {
      activeChapterId: activeChapterId.value,
      clearSearch: Boolean(clearSearch)
    }
  }

  const removeChapter = (chapterId, nextActiveChapterId = '') => {
    const id = String(chapterId || '')
    chapters.value = sortByOrderIndex(
      chapters.value
        .filter((item) => item.id !== id)
        .map((item, index) => ({ ...item, order_index: index + 1 }))
    )
    if (activeChapterId.value === id) {
      activeChapterId.value = String(nextActiveChapterId || chapters.value[0]?.id || '')
    }
    const nextDraftMap = { ...draftByChapterId.value }
    delete nextDraftMap[id]
    draftByChapterId.value = nextDraftMap
    const nextTitleDraftMap = { ...draftTitleByChapterId.value }
    delete nextTitleDraftMap[id]
    draftTitleByChapterId.value = nextTitleDraftMap
  }

  const reorderChapters = (orderedIds) => {
    const sequence = Array.isArray(orderedIds) ? orderedIds.map((item) => String(item || '')) : []
    const byId = new Map(chapters.value.map((item) => [String(item.id), item]))
    const reordered = sequence.map((id) => byId.get(id)).filter(Boolean)
    const remaining = chapters.value.filter((item) => !sequence.includes(String(item.id)))
    chapters.value = [...reordered, ...remaining].map((item, index) => ({
      ...item,
      order_index: index + 1
    }))
  }

  const getFilteredChapters = (keyword = '') => {
    const query = String(keyword || '').trim().toLowerCase()
    if (!query) {
      return [...chapters.value]
    }
    return chapters.value.filter((chapter, index) => {
      const displayNumber = `第${Number(chapter.order_index || index + 1)}章`
      const title = String(chapter.title || '').toLowerCase()
      return title.includes(query) || displayNumber.toLowerCase().includes(query)
    })
  }

  const updateChapterDraft = (chapterId, content) => {
    const id = String(chapterId || '')
    if (!id) return
    draftByChapterId.value = {
      ...draftByChapterId.value,
      [id]: String(content || '')
    }
  }

  const clearChapterDraft = (chapterId) => {
    const id = String(chapterId || '')
    if (!id || !Object.prototype.hasOwnProperty.call(draftByChapterId.value, id)) return
    const nextDraftMap = { ...draftByChapterId.value }
    delete nextDraftMap[id]
    draftByChapterId.value = nextDraftMap
  }

  const updateChapterTitleDraft = (chapterId, title) => {
    const id = String(chapterId || '')
    if (!id) return
    draftTitleByChapterId.value = {
      ...draftTitleByChapterId.value,
      [id]: String(title || '')
    }
  }

  const clearChapterTitleDraft = (chapterId) => {
    const id = String(chapterId || '')
    if (!id || !Object.prototype.hasOwnProperty.call(draftTitleByChapterId.value, id)) return
    const nextDraftMap = { ...draftTitleByChapterId.value }
    delete nextDraftMap[id]
    draftTitleByChapterId.value = nextDraftMap
  }

  return {
    chapters,
    activeChapterId,
    draftByChapterId,
    draftTitleByChapterId,
    chapterCount,
    activeChapter,
    activeChapterContent,
    activeChapterTitle,
    setChapters,
    setActiveChapter,
    upsertChapter,
    appendCreatedChapter,
    removeChapter,
    reorderChapters,
    getFilteredChapters,
    updateChapterDraft,
    clearChapterDraft,
    updateChapterTitleDraft,
    clearChapterTitleDraft
  }
})
