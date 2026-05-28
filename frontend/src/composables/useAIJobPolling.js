import { computed, onScopeDispose, ref } from 'vue'
import { aiApi } from '@/api'

const DEFAULT_TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled', 'partial_success'])

export const useAIJobPolling = ({
  intervalMs = 1000,
  maxIntervalMs = 5000,
  fetchJob = (jobId) => aiApi.getAIJob(jobId),
  terminalStatuses = DEFAULT_TERMINAL_STATUSES,
  sse = {}
} = {}) => {
  const job = ref(null)
  const loading = ref(false)
  const error = ref('')
  const jobId = ref('')
  const pollingHint = ref({})
  const transport = ref('polling')
  let timer = null
  let eventSource = null

  const status = computed(() => String(job.value?.status || ''))
  const isTerminal = computed(() => terminalStatuses.has(status.value))

  const clearTimer = () => {
    if (!timer) return
    clearTimeout(timer)
    timer = null
  }

  const closeEventSource = () => {
    if (!eventSource) return
    eventSource.close?.()
    eventSource = null
  }

  const stop = () => {
    clearTimer()
    closeEventSource()
    transport.value = 'polling'
  }

  const unwrapPayload = (payload) => {
    const nextData = payload?.data ?? payload ?? {}
    const nextHint = payload?.polling_hint ?? nextData?.polling_hint ?? {}
    return {
      data: nextData,
      hint: nextHint && typeof nextHint === 'object' ? nextHint : {}
    }
  }

  const resolveIntervalMs = () => {
    const hinted = Number(pollingHint.value?.next_interval_ms || 0)
    if (Number.isFinite(hinted) && hinted > 0) {
      return Math.min(hinted, maxIntervalMs)
    }
    return intervalMs
  }

  const scheduleNextFetch = () => {
    clearTimer()
    if (!jobId.value || isTerminal.value || pollingHint.value?.stop) return
    timer = setTimeout(() => {
      void fetchOnce()
    }, resolveIntervalMs())
  }

  const fallbackToPolling = () => {
    closeEventSource()
    transport.value = 'polling'
    scheduleNextFetch()
  }

  const connectEventSource = () => {
    if (!sse?.enabled || !jobId.value) return
    const buildUrl = typeof sse.buildUrl === 'function' ? sse.buildUrl : null
    const eventSourceFactory = typeof sse.eventSourceFactory === 'function'
      ? sse.eventSourceFactory
      : (typeof window !== 'undefined' ? (url) => new window.EventSource(url) : null)
    if (!buildUrl || !eventSourceFactory) return
    try {
      eventSource = eventSourceFactory(buildUrl(jobId.value))
      transport.value = 'sse'
      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(String(event?.data || '{}'))
          if (parsed?.data) {
            job.value = parsed.data
          }
          if (parsed?.polling_hint && typeof parsed.polling_hint === 'object') {
            pollingHint.value = parsed.polling_hint
          }
          if (terminalStatuses.has(String(job.value?.status || '')) || pollingHint.value?.stop) {
            stop()
          }
        } catch {
          fallbackToPolling()
        }
      }
      eventSource.onerror = () => {
        fallbackToPolling()
      }
    } catch {
      fallbackToPolling()
    }
  }

  const fetchOnce = async () => {
    if (!jobId.value) return null
    loading.value = true
    error.value = ''
    try {
      const payload = await fetchJob(jobId.value)
      const nextPayload = unwrapPayload(payload)
      job.value = nextPayload.data
      pollingHint.value = nextPayload.hint
      if (terminalStatuses.has(String(job.value?.status || '')) || pollingHint.value?.stop) {
        stop()
      } else if (transport.value !== 'sse') {
        scheduleNextFetch()
      }
      return job.value
    } catch (err) {
      error.value = String(err?.userMessage || err?.message || 'job polling failed')
      stop()
      return null
    } finally {
      loading.value = false
    }
  }

  const start = async (nextJobId) => {
    jobId.value = String(nextJobId || '')
    pollingHint.value = {}
    stop()
    if (!jobId.value) return
    await fetchOnce()
    if (!jobId.value || terminalStatuses.has(String(job.value?.status || '')) || pollingHint.value?.stop) {
      return
    }
    if (sse?.enabled) {
      connectEventSource()
      if (transport.value === 'sse') {
        return
      }
    }
    scheduleNextFetch()
  }

  onScopeDispose(stop)

  return {
    job,
    jobId,
    status,
    isTerminal,
    loading,
    error,
    pollingHint,
    transport,
    start,
    stop,
    fetchOnce
  }
}
