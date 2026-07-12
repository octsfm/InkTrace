import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const upsertAutoQueueConfig = vi.fn()
const getAutoQueueConfig = vi.fn()
const startAutoQueue = vi.fn()
const getAutoQueueStatus = vi.fn()
const getAutoQueueHistory = vi.fn()
const pauseAutoQueue = vi.fn()
const resumeAutoQueue = vi.fn()
const stopAutoQueue = vi.fn()
const confirmAutoQueueContinue = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    upsertAutoQueueConfig,
    getAutoQueueConfig,
    startAutoQueue,
    getAutoQueueStatus,
    getAutoQueueHistory,
    pauseAutoQueue,
    resumeAutoQueue,
    stopAutoQueue,
    confirmAutoQueueContinue
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_auto_queue'
}))

describe('useAutoQueueStore', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.useFakeTimers()
    setActivePinia(createPinia())
  })

  it('loads config and history for the current work, then restores polling for active run', async () => {
    const { useAutoQueueStore } = await import('../useAutoQueueStore')
    const store = useAutoQueueStore()

    getAutoQueueConfig.mockResolvedValue({
      data: {
        config: {
          config_id: 'aqc_001',
          work_id: 'work-1',
          target_chapters: 5
        }
      }
    })
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [
          { run_id: 'aqr_active_001', status: 'running', generated_count: 2 },
          { run_id: 'aqr_stopped_001', status: 'stopped', generated_count: 1 }
        ]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: {
          run_id: 'aqr_active_001',
          status: 'running',
          generated_count: 2
        }
      }
    })

    await store.initializeForWork('work-1')

    expect(getAutoQueueConfig).toHaveBeenCalledWith('work-1')
    expect(getAutoQueueHistory).toHaveBeenCalledWith('work-1')
    expect(getAutoQueueStatus).toHaveBeenCalledWith('aqr_active_001')
    expect(store.featureEnabled).toBe(true)
    expect(store.config?.config_id).toBe('aqc_001')
    expect(store.currentRun?.run_id).toBe('aqr_active_001')
    expect(store.historyRuns.map((item) => item.run_id)).toEqual(['aqr_active_001', 'aqr_stopped_001'])
  })

  it('saves config, starts queue, polls until waiting user decision, and exposes waiting state', async () => {
    const { useAutoQueueStore } = await import('../useAutoQueueStore')
    const store = useAutoQueueStore()

    getAutoQueueConfig.mockResolvedValue({ data: { config: null } })
    getAutoQueueHistory.mockResolvedValue({ data: { runs: [] } })
    upsertAutoQueueConfig.mockResolvedValue({
      data: {
        config: {
          config_id: 'aqc_002',
          work_id: 'work-1',
          target_chapters: 6
        }
      }
    })
    startAutoQueue.mockResolvedValue({
      data: {
        run_id: 'aqr_002',
        status: 'running',
      }
    })
    getAutoQueueStatus
      .mockResolvedValueOnce({
        data: {
          run: {
            run_id: 'aqr_002',
            status: 'running',
            generated_count: 1,
            polling_hint: { next_interval_ms: 2500, stop: false }
          }
        }
      })
      .mockResolvedValueOnce({
        data: {
          run: {
            run_id: 'aqr_002',
            status: 'waiting_user_decision',
            generated_count: 2
          },
          polling_hint: { stop: true }
        }
      })

    await store.initializeForWork('work-1')
    await store.saveConfig({ target_chapters: 6 })
    await store.startQueue({ startChapterId: 'chapter-1', userInstruction: '让人物关系推进' })

    expect(upsertAutoQueueConfig).toHaveBeenCalledWith({
      work_id: 'work-1',
      target_chapters: 6
    })
    expect(startAutoQueue).toHaveBeenCalledWith({
      work_id: 'work-1',
      start_chapter_id: 'chapter-1',
      user_instruction: '让人物关系推进'
    })
    expect(store.currentRun?.run_id).toBe('aqr_002')
    expect(store.currentRun?.status).toBe('running')

    await store.statusPolling.fetchOnce()

    expect(store.currentRun?.run_id).toBe('aqr_002')
    expect(store.currentRun?.status).toBe('waiting_user_decision')
    expect(store.waitingUserDecision).toBe(true)
  })

  it('sends user_action payloads for pause resume stop and confirm-continue actions', async () => {
    const { useAutoQueueStore } = await import('../useAutoQueueStore')
    const store = useAutoQueueStore()

    getAutoQueueConfig.mockResolvedValue({ data: { config: null } })
    getAutoQueueHistory.mockResolvedValue({
      data: {
        runs: [{ run_id: 'aqr_003', status: 'waiting_user_decision', generated_count: 3 }]
      }
    })
    getAutoQueueStatus.mockResolvedValue({
      data: {
        run: { run_id: 'aqr_003', status: 'waiting_user_decision', generated_count: 3 }
      }
    })
    pauseAutoQueue.mockResolvedValue({
      data: {
        run: { run_id: 'aqr_003', status: 'paused', generated_count: 3 }
      }
    })
    resumeAutoQueue.mockResolvedValue({
      data: {
        run: { run_id: 'aqr_003', status: 'running', generated_count: 3 }
      }
    })
    stopAutoQueue.mockResolvedValue({
      data: {
        run: { run_id: 'aqr_003', status: 'stopped', generated_count: 3 }
      }
    })
    confirmAutoQueueContinue.mockResolvedValue({
      data: {
        run: { run_id: 'aqr_003', status: 'running', generated_count: 4 }
      }
    })

    await store.initializeForWork('work-1')
    await store.pauseQueue('aqr_003')
    await store.resumeQueue('aqr_003')
    await store.confirmContinue('aqr_003')
    await store.stopQueue('aqr_003')

    expect(pauseAutoQueue).toHaveBeenCalledWith('aqr_003', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(resumeAutoQueue).toHaveBeenCalledWith('aqr_003', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(confirmAutoQueueContinue).toHaveBeenCalledWith('aqr_003', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(stopAutoQueue).toHaveBeenCalledWith('aqr_003', expect.objectContaining({
      caller_type: 'user_action',
      user_action: true
    }))
    expect(store.currentRun?.status).toBe('stopped')
  })
})
