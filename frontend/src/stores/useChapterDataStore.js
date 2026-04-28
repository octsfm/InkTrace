import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useChapterDataStore = defineStore('chapterData', () => {
  const chapters = ref([])
  const activeChapterId = ref('')
  const draftByChapterId = ref({})

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

  const setChapters = (items) => {
    chapters.value = Array.isArray(items) ? [...items] : []
  }

  const setActiveChapter = (chapterId) => {
    activeChapterId.value = String(chapterId || '')
  }

  const upsertChapter = (chapter) => {
    if (!chapter || !chapter.id) return
    const index = chapters.value.findIndex((item) => item.id === chapter.id)
    if (index < 0) {
      chapters.value.push(chapter)
      return
    }
    chapters.value[index] = { ...chapters.value[index], ...chapter }
  }

  const removeChapter = (chapterId) => {
    const id = String(chapterId || '')
    chapters.value = chapters.value.filter((item) => item.id !== id)
    if (activeChapterId.value === id) {
      activeChapterId.value = chapters.value[0]?.id || ''
    }
    const nextDraftMap = { ...draftByChapterId.value }
    delete nextDraftMap[id]
    draftByChapterId.value = nextDraftMap
  }

  const reorderChapters = (orderedIds) => {
    const sequence = Array.isArray(orderedIds) ? orderedIds.map((item) => String(item || '')) : []
    const byId = new Map(chapters.value.map((item) => [String(item.id), item]))
    const reordered = sequence.map((id) => byId.get(id)).filter(Boolean)
    const remaining = chapters.value.filter((item) => !sequence.includes(String(item.id)))
    chapters.value = [...reordered, ...remaining]
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

  return {
    chapters,
    activeChapterId,
    draftByChapterId,
    chapterCount,
    activeChapter,
    activeChapterContent,
    setChapters,
    setActiveChapter,
    upsertChapter,
    removeChapter,
    reorderChapters,
    updateChapterDraft,
    clearChapterDraft
  }
})
