import { effectScope } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAIJobPolling } from './useAIJobPolling'

describe('useAIJobPolling', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('uses polling_hint.next_interval_ms and stops when polling_hint.stop is true', async () => {
    vi.useFakeTimers()
    const fetchJob = vi.fn()
      .mockResolvedValueOnce({
        data: { job_id: 'job-1', status: 'running' },
        polling_hint: { next_interval_ms: 2400, stop: false }
      })
      .mockResolvedValueOnce({
        data: { job_id: 'job-1', status: 'completed' },
        polling_hint: { next_interval_ms: 5000, stop: true }
      })

    const scope = effectScope()
    const polling = scope.run(() => useAIJobPolling({ intervalMs: 1000, fetchJob }))

    await polling.start('job-1')
    expect(fetchJob).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(2300)
    expect(fetchJob).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(200)
    expect(fetchJob).toHaveBeenCalledTimes(2)
    expect(polling.status.value).toBe('completed')

    await vi.advanceTimersByTimeAsync(6000)
    expect(fetchJob).toHaveBeenCalledTimes(2)

    scope.stop()
  })

  it('falls back to polling when sse subscription errors', async () => {
    vi.useFakeTimers()
    const fetchJob = vi.fn()
      .mockResolvedValueOnce({
        data: { job_id: 'job-2', status: 'running' },
        polling_hint: { next_interval_ms: 1200, stop: false }
      })
      .mockResolvedValueOnce({
        data: { job_id: 'job-2', status: 'completed' },
        polling_hint: { stop: true }
      })

    let currentSource = null
    const eventSourceFactory = vi.fn((url) => {
      currentSource = {
        url,
        close: vi.fn(),
        onmessage: null,
        onerror: null
      }
      return currentSource
    })

    const scope = effectScope()
    const polling = scope.run(() => useAIJobPolling({
      intervalMs: 1000,
      fetchJob,
      sse: {
        enabled: true,
        buildUrl: (jobId) => `/api/v2/ai/jobs/${jobId}/events`,
        eventSourceFactory
      }
    }))

    await polling.start('job-2')
    expect(eventSourceFactory).toHaveBeenCalledWith('/api/v2/ai/jobs/job-2/events')
    expect(fetchJob).toHaveBeenCalledTimes(1)

    currentSource.onerror?.(new Error('sse unavailable'))
    await vi.advanceTimersByTimeAsync(1200)

    expect(fetchJob).toHaveBeenCalledTimes(2)
    expect(currentSource.close).toHaveBeenCalled()
    expect(polling.status.value).toBe('completed')

    scope.stop()
  })
})
