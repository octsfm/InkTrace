import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const startStyleDNAExtract = vi.fn()
const getStyleProfile = vi.fn()
const getActiveStyleProfile = vi.fn()
const getStyleProfileHistory = vi.fn()
const confirmStyleProfile = vi.fn()
const disableStyleProfile = vi.fn()
const deleteStyleProfile = vi.fn()
const getAIJob = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    startStyleDNAExtract,
    getStyleProfile,
    getActiveStyleProfile,
    getStyleProfileHistory,
    confirmStyleProfile,
    disableStyleProfile,
    deleteStyleProfile,
    getAIJob
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_style_dna'
}))

describe('useStyleDNAStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    setActivePinia(createPinia())
    window.sessionStorage.clear()
  })

  it('loads active profile and history for the current work', async () => {
    const { useStyleDNAStore } = await import('../useStyleDNAStore')
    const store = useStyleDNAStore()

    getActiveStyleProfile.mockResolvedValue({
      data: {
        profile: { profile_id: 'sp_active_001', status: 'active', style_summary: '简洁冷峻。', confidence: 0.83 }
      }
    })
    getStyleProfileHistory.mockResolvedValue({
      data: {
        profiles: [
          { profile_id: 'sp_pending_001', status: 'pending_confirm', version: 2 },
          { profile_id: 'sp_active_001', status: 'active', version: 1 }
        ]
      }
    })

    await store.initializeForWork('work-1')

    expect(getActiveStyleProfile).toHaveBeenCalledWith('work-1')
    expect(getStyleProfileHistory).toHaveBeenCalledWith('work-1')
    expect(store.featureEnabled).toBe(true)
    expect(store.activeProfile?.profile_id).toBe('sp_active_001')
    expect(store.currentProfile?.profile_id).toBe('sp_active_001')
    expect(store.historyProfiles.map((item) => item.profile_id)).toEqual(['sp_pending_001', 'sp_active_001'])
  })

  it('falls back to latest history profile when no active profile exists', async () => {
    const { useStyleDNAStore } = await import('../useStyleDNAStore')
    const store = useStyleDNAStore()

    getActiveStyleProfile.mockResolvedValue({ data: { profile: null } })
    getStyleProfileHistory.mockResolvedValue({
      data: {
        profiles: [
          { profile_id: 'sp_pending_002', status: 'pending_confirm', version: 3 },
          { profile_id: 'sp_archived_001', status: 'archived', version: 2 }
        ]
      }
    })

    await store.initializeForWork('work-1')

    expect(store.currentProfile?.profile_id).toBe('sp_pending_002')
  })

  it('starts extract job, restores pending job state, and refreshes profile on completion', async () => {
    const { useStyleDNAStore } = await import('../useStyleDNAStore')
    const store = useStyleDNAStore()

    getActiveStyleProfile.mockResolvedValue({ data: { profile: null } })
    getStyleProfileHistory.mockResolvedValue({ data: { profiles: [] } })
    startStyleDNAExtract.mockResolvedValue({
      data: {
        job_id: 'job_style_001',
        status: 'queued',
        polling_hint: { next_poll_after_ms: 3000 }
      }
    })
    getAIJob
      .mockResolvedValueOnce({
        data: { job_id: 'job_style_001', status: 'running' },
        polling_hint: { next_interval_ms: 3000, stop: false }
      })
      .mockResolvedValueOnce({
        data: {
          job_id: 'job_style_001',
          status: 'completed',
          result_summary: {
            profile_id: 'sp_pending_001',
            profile_status: 'pending_confirm',
            warning_code: 'P2_STYLE_LOW_CONFIDENCE'
          }
        },
        polling_hint: { stop: true }
      })
    getStyleProfile.mockResolvedValue({
      data: {
        profile: {
          profile_id: 'sp_pending_001',
          status: 'pending_confirm',
          confidence: 0.42,
          low_confidence_reason: 'source_text_too_short',
          style_summary: '短句为主。'
        }
      }
    })
    getStyleProfileHistory
      .mockResolvedValueOnce({ data: { profiles: [] } })
      .mockResolvedValueOnce({
        data: {
          profiles: [
            { profile_id: 'sp_pending_001', status: 'pending_confirm', confidence: 0.42 }
          ]
        }
      })

    await store.initializeForWork('work-1')
    await store.startExtract({
      sourceText: '这是用于提取风格画像的标杆文本。'.repeat(60),
      sourceType: 'user_upload',
      sourceRef: 'upload_001'
    })

    expect(startStyleDNAExtract).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      source_type: 'user_upload',
      source_ref: 'upload_001',
      caller_type: 'user_action'
    }))
    expect(window.sessionStorage.getItem('inktrace.style-dna.pending:work-1')).toContain('job_style_001')

    await vi.advanceTimersByTimeAsync(3000)

    expect(getAIJob).toHaveBeenCalledTimes(2)
    expect(getStyleProfile).toHaveBeenCalledWith('sp_pending_001')
    expect(store.currentProfile?.profile_id).toBe('sp_pending_001')
    expect(store.warningMessage).toContain('置信度较低')
    expect(window.sessionStorage.getItem('inktrace.style-dna.pending:work-1')).toBeNull()
  })

  it('builds chapter_reference source text from up to three published chapters and excludes drafts', async () => {
    const { useStyleDNAStore } = await import('../useStyleDNAStore')
    const store = useStyleDNAStore()

    getActiveStyleProfile.mockResolvedValue({ data: { profile: null } })
    getStyleProfileHistory.mockResolvedValue({ data: { profiles: [] } })
    startStyleDNAExtract.mockResolvedValue({
      data: {
        job_id: 'job_style_002',
        status: 'queued',
        polling_hint: { next_poll_after_ms: 3000 }
      }
    })
    getAIJob.mockResolvedValue({
      data: { job_id: 'job_style_002', status: 'completed', result_summary: { profile_id: 'sp_pending_002' } },
      polling_hint: { stop: true }
    })
    getStyleProfile.mockResolvedValue({ data: { profile: { profile_id: 'sp_pending_002', status: 'pending_confirm' } } })

    await store.initializeForWork('work-1')
    await store.startExtract({
      sourceType: 'chapter_reference',
      sourceChapterIds: ['chapter-1', 'chapter-2', 'chapter-3', 'chapter-4'],
      availableChapters: [
        { id: 'chapter-1', title: '一', content: '第一章正文', status: 'published', order_index: 1 },
        { id: 'chapter-2', title: '二', content: '第二章正文', status: 'published', order_index: 2 },
        { id: 'chapter-3', title: '三', content: '第三章正文', status: 'draft', order_index: 3 },
        { id: 'chapter-4', title: '四', content: '第四章正文', status: 'published', order_index: 4 }
      ],
      draftChapterIds: ['chapter-4']
    })

    expect(startStyleDNAExtract).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      source_type: 'chapter_reference',
      source_ref: 'chapter-1,chapter-2',
      source_text: expect.stringContaining('第一章正文')
    }))
    expect(startStyleDNAExtract).toHaveBeenCalledWith(expect.objectContaining({
      source_text: expect.not.stringContaining('第三章正文')
    }))
    expect(startStyleDNAExtract).toHaveBeenCalledWith(expect.objectContaining({
      source_text: expect.not.stringContaining('第四章正文')
    }))
  })
})
