import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { isP2FeatureEnabled } from '@/config/p2FeatureFlags'

const DEFAULT_ENTITY_TYPES = ['character', 'event', 'foreshadow']

const unwrapData = (payload) => payload?.data ?? payload ?? {}

const buildMentionPayload = (item) => ({
  mention_id: String(item?.mention_id || ''),
  entity_type: String(item?.entity_type || ''),
  entity_id: String(item?.entity_id || ''),
  entity_name_snapshot: String(item?.entity_name_snapshot || item?.entity_name || ''),
  start_pos: Number(item?.start_pos || 0),
  end_pos: Number(item?.end_pos || 0),
  source: String(item?.source || 'user_input'),
  ai_suggestion_id: String(item?.ai_suggestion_id || '')
})

const detectMentionQuery = (content, cursorPosition) => {
  const prefix = String(content || '').slice(0, Math.max(0, Number(cursorPosition || 0)))
  const match = prefix.match(/@([^\s@]*)$/)
  if (!match) {
    return null
  }
  return {
    query: String(match[1] || ''),
    triggerStart: prefix.lastIndexOf('@'),
    triggerEnd: prefix.length
  }
}

export const useMentionStore = defineStore('workbenchMention', () => {
  const workId = ref('')
  const chapterId = ref('')
  const chapterRevision = ref(0)
  const mentions = ref([])
  const mentionsByChapterId = ref({})
  const suggestions = ref([])
  const popupVisible = ref(false)
  const popupPosition = ref({ x: 0, y: 0 })
  const activeQuery = ref('')
  const triggerRange = ref({ start: 0, end: 0 })
  const featureEnabled = computed(() => isP2FeatureEnabled('enable_mentions'))

  const setChapterMentions = (targetChapterId, nextMentions) => {
    const normalizedChapterId = String(targetChapterId || '')
    if (!normalizedChapterId) {
      mentions.value = Array.isArray(nextMentions) ? [...nextMentions] : []
      return mentions.value
    }
    const normalizedMentions = Array.isArray(nextMentions) ? [...nextMentions] : []
    mentionsByChapterId.value = {
      ...mentionsByChapterId.value,
      [normalizedChapterId]: normalizedMentions
    }
    if (normalizedChapterId === String(chapterId.value || '')) {
      mentions.value = normalizedMentions
    }
    return normalizedMentions
  }

  const closePopup = () => {
    popupVisible.value = false
    activeQuery.value = ''
    suggestions.value = []
    triggerRange.value = { start: 0, end: 0 }
  }

  const initializeContext = ({
    workId: nextWorkId = '',
    chapterId: nextChapterId = '',
    chapterRevision: nextChapterRevision = 0
  } = {}) => {
    const contextChanged = String(chapterId.value || '') !== String(nextChapterId || '')
      || String(workId.value || '') !== String(nextWorkId || '')
    workId.value = String(nextWorkId || '')
    chapterId.value = String(nextChapterId || '')
    chapterRevision.value = Number(nextChapterRevision || 0)
    if (contextChanged) {
      mentions.value = Array.isArray(mentionsByChapterId.value[chapterId.value])
        ? [...mentionsByChapterId.value[chapterId.value]]
        : []
      closePopup()
    }
  }

  const loadMentions = async (targetChapterId = chapterId.value) => {
    if (!featureEnabled.value || !targetChapterId) return []
    closePopup()
    const payload = unwrapData(await aiApi.getChapterMentions(String(targetChapterId || '')))
    return setChapterMentions(targetChapterId, Array.isArray(payload?.mentions) ? payload.mentions : [])
  }

  const fetchSuggestions = async (query) => {
    if (!featureEnabled.value || !workId.value) return []
    const payload = unwrapData(await aiApi.suggestMentions({
      work_id: workId.value,
      q: String(query || ''),
      types: DEFAULT_ENTITY_TYPES.join(','),
      limit: 10
    }))
    suggestions.value = Array.isArray(payload?.suggestions) ? payload.suggestions : []
    popupVisible.value = suggestions.value.length > 0
    return suggestions.value
  }

  const inspectTrigger = async ({
    content = '',
    cursorPosition = 0,
    popupPosition: nextPopupPosition = null
  } = {}) => {
    if (!featureEnabled.value) return []
    const detected = detectMentionQuery(content, cursorPosition)
    if (!detected) {
      closePopup()
      return []
    }
    activeQuery.value = detected.query
    triggerRange.value = {
      start: detected.triggerStart,
      end: detected.triggerEnd
    }
    if (nextPopupPosition && Number.isFinite(nextPopupPosition.x) && Number.isFinite(nextPopupPosition.y)) {
      popupPosition.value = {
        x: Number(nextPopupPosition.x),
        y: Number(nextPopupPosition.y)
      }
    }
    return fetchSuggestions(detected.query)
  }

  const registerInsertedMention = (suggestion, { start = 0, end = 0 } = {}) => {
    const nextMention = {
      mention_id: '',
      entity_type: String(suggestion?.entity_type || ''),
      entity_id: String(suggestion?.entity_id || ''),
      entity_name_snapshot: String(suggestion?.entity_name || ''),
      start_pos: Number(start || 0),
      end_pos: Number(end || 0),
      source: 'user_input',
      ai_suggestion_id: ''
    }
    setChapterMentions(chapterId.value, [...mentions.value, nextMention])
    closePopup()
    return nextMention
  }

  const rebuildMentionRanges = (content, sourceMentions = mentions.value) => {
    let searchOffset = 0
    return sourceMentions.map((item) => {
      const needle = `@${String(item?.entity_name_snapshot || '')}`
      const nextIndex = String(content || '').indexOf(needle, searchOffset)
      if (nextIndex < 0) {
        return {
          ...item,
          source: 'user_input'
        }
      }
      searchOffset = nextIndex + needle.length
      return {
        ...item,
        start_pos: nextIndex,
        end_pos: nextIndex + needle.length,
        source: 'user_input'
      }
    })
  }

  const saveMentions = async (content, options = {}) => {
    const targetChapterId = String(options?.targetChapterId || chapterId.value || '')
    const targetChapterRevision = Number(options?.chapterRevision ?? chapterRevision.value ?? 0)
    if (!featureEnabled.value || !targetChapterId) return []
    const sourceMentions = targetChapterId === String(chapterId.value || '')
      ? mentions.value
      : Array.isArray(mentionsByChapterId.value[targetChapterId])
        ? mentionsByChapterId.value[targetChapterId]
        : []
    const rebuilt = rebuildMentionRanges(content, sourceMentions)
    const payload = unwrapData(await aiApi.replaceChapterMentions(targetChapterId, {
      chapter_revision: targetChapterRevision,
      mentions: rebuilt.map(buildMentionPayload)
    }))
    return setChapterMentions(targetChapterId, Array.isArray(payload?.mentions) ? payload.mentions : [])
  }

  return {
    workId,
    chapterId,
    chapterRevision,
    mentions,
    suggestions,
    popupVisible,
    popupPosition,
    activeQuery,
    triggerRange,
    featureEnabled,
    initializeContext,
    closePopup,
    loadMentions,
    fetchSuggestions,
    inspectTrigger,
    registerInsertedMention,
    saveMentions
  }
})
