import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const suggestMentions = vi.fn()
const getChapterMentions = vi.fn()
const replaceChapterMentions = vi.fn()
const getMentionSummary = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    suggestMentions,
    getChapterMentions,
    replaceChapterMentions,
    getMentionSummary
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_mentions'
}))

describe('useMentionStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('detects active @ trigger before cursor and loads suggestions', async () => {
    const { useMentionStore } = await import('../useMentionStore')
    const store = useMentionStore()

    suggestMentions.mockResolvedValue({
      data: {
        suggestions: [{
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name: '张三',
          match_type: 'prefix',
          summary_preview: '主角'
        }]
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3
    })
    await store.inspectTrigger({
      content: '他说@张',
      cursorPosition: 4
    })

    expect(suggestMentions).toHaveBeenCalledWith({
      work_id: 'work-1',
      q: '张',
      types: 'character,event,foreshadow',
      limit: 10
    })
    expect(store.popupVisible).toBe(true)
    expect(store.activeQuery).toBe('张')
    expect(store.suggestions[0].entity_id).toBe('char_001')
  })

  it('registers inserted mention and rebuilds positions before save', async () => {
    const { useMentionStore } = await import('../useMentionStore')
    const store = useMentionStore()

    replaceChapterMentions.mockResolvedValue({
      data: {
        mentions: [{
          mention_id: 'm_001',
          chapter_id: 'chapter-1',
          work_id: 'work-1',
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name_snapshot: '张三',
          start_pos: 2,
          end_pos: 5,
          source: 'user_input',
          status: 'active',
          is_active: true,
          ai_suggestion_id: '',
          validation_detail: '',
          created_at: '2026-07-03T12:00:00Z',
          updated_at: '2026-07-03T12:00:00Z'
        }]
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3
    })
    store.registerInsertedMention(
      {
        entity_type: 'character',
        entity_id: 'char_001',
        entity_name: '张三'
      },
      {
        start: 2,
        end: 5
      }
    )

    const saved = await store.saveMentions('他说@张三')

    expect(replaceChapterMentions).toHaveBeenCalledWith('chapter-1', {
      chapter_revision: 3,
      mentions: [{
        mention_id: '',
        entity_type: 'character',
        entity_id: 'char_001',
        entity_name_snapshot: '张三',
        start_pos: 2,
        end_pos: 5,
        source: 'user_input',
        ai_suggestion_id: ''
      }]
    })
    expect(saved[0].mention_id).toBe('m_001')
    expect(store.mentions[0].mention_id).toBe('m_001')
  })

  it('loads existing chapter mentions and clears popup state when chapter changes', async () => {
    const { useMentionStore } = await import('../useMentionStore')
    const store = useMentionStore()

    getChapterMentions.mockResolvedValue({
      data: {
        mentions: [{
          mention_id: 'm_001',
          chapter_id: 'chapter-2',
          work_id: 'work-1',
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name_snapshot: '张三',
          start_pos: 4,
          end_pos: 7,
          source: 'user_input',
          status: 'active',
          is_active: true,
          ai_suggestion_id: '',
          validation_detail: '',
          created_at: '2026-07-03T12:00:00Z',
          updated_at: '2026-07-03T12:00:00Z'
        }]
      }
    })

    store.popupVisible = true
    store.activeQuery = '张'
    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-2',
      chapterRevision: 4
    })
    const mentions = await store.loadMentions('chapter-2')

    expect(store.popupVisible).toBe(false)
    expect(store.activeQuery).toBe('')
    expect(mentions[0].mention_id).toBe('m_001')
    expect(store.mentions[0].start_pos).toBe(4)
  })

  it('tracks active suggestion index and cycles with keyboard navigation', async () => {
    const { useMentionStore } = await import('../useMentionStore')
    const store = useMentionStore()

    suggestMentions.mockResolvedValue({
      data: {
        suggestions: [{
          entity_type: 'character',
          entity_id: 'char_001',
          entity_name: '张三',
          match_type: 'prefix',
          summary_preview: '主角'
        }, {
          entity_type: 'event',
          entity_id: 'event_001',
          entity_name: '雨夜决战',
          match_type: 'prefix',
          summary_preview: '关键事件'
        }]
      }
    })

    store.initializeContext({
      workId: 'work-1',
      chapterId: 'chapter-1',
      chapterRevision: 3
    })

    await store.inspectTrigger({
      content: '他说@张',
      cursorPosition: 4
    })

    expect(store.activeSuggestionIndex).toBe(0)
    expect(store.getActiveSuggestion().entity_id).toBe('char_001')

    store.moveActiveSuggestion(1)
    expect(store.activeSuggestionIndex).toBe(1)
    expect(store.getActiveSuggestion().entity_id).toBe('event_001')

    store.moveActiveSuggestion(1)
    expect(store.activeSuggestionIndex).toBe(0)

    store.moveActiveSuggestion(-1)
    expect(store.activeSuggestionIndex).toBe(1)

    store.closePopup()
    expect(store.activeSuggestionIndex).toBe(-1)
    expect(store.getActiveSuggestion()).toBe(null)
  })

  it('loads mention summary once and reuses cached result for the same mention', async () => {
    const { useMentionStore } = await import('../useMentionStore')
    const store = useMentionStore()

    getMentionSummary.mockResolvedValue({
      data: {
        mention_id: 'm_001',
        entity_type: 'character',
        entity_id: 'char_001',
        entity_name_snapshot: '张三',
        entity_current_name: '张三',
        summary_text: '张三是本书主角。',
        status: 'active'
      }
    })

    const first = await store.loadMentionSummary('m_001')
    const second = await store.loadMentionSummary('m_001')

    expect(getMentionSummary).toHaveBeenCalledTimes(1)
    expect(first.summary_text).toContain('主角')
    expect(second.summary_text).toContain('主角')
    expect(store.mentionSummaryById.m_001.summary_text).toContain('主角')
  })

  it('builds status-specific mention helper messages from summary payload', async () => {
    const { useMentionStore } = await import('../useMentionStore')
    const store = useMentionStore()

    expect(store.describeMentionSummary({
      status: 'broken',
      entity_name_snapshot: '张三',
      entity_current_name: '张三',
      summary_text: '原摘要'
    })).toContain('已失效')

    expect(store.describeMentionSummary({
      status: 'stale',
      entity_name_snapshot: '张三',
      entity_current_name: '张小凡',
      summary_text: '原摘要'
    })).toContain('已更名')

    expect(store.describeMentionSummary({
      status: 'inactive_entity',
      entity_name_snapshot: '张三',
      entity_current_name: '张三',
      summary_text: '原摘要'
    })).toContain('已删除')

    expect(store.describeMentionSummary({
      status: 'active',
      entity_name_snapshot: '张三',
      entity_current_name: '张三',
      summary_text: '张三是本书主角。'
    })).toContain('张三是本书主角')
  })
})
