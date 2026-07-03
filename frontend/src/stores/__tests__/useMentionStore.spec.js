import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const suggestMentions = vi.fn()
const getChapterMentions = vi.fn()
const replaceChapterMentions = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    suggestMentions,
    getChapterMentions,
    replaceChapterMentions
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
})
