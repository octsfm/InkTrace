import { computed, onBeforeUnmount, ref } from 'vue'
import { aiApi } from '@/api'

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled', 'partial_success'])

export const useAIJobPolling = ({ intervalMs = 1000 } = {}) => {
  const job = ref(null)
  const loading = ref(false)
  const error = ref('')
  const jobId = ref('')
  let timer = null

  const status = computed(() => String(job.value?.status || ''))
  const isTerminal = computed(() => TERMINAL_STATUSES.has(status.value))

  const stop = () => {
    if (!timer) return
    clearInterval(timer)
    timer = null
  }

  const fetchOnce = async () => {
    if (!jobId.value) return null
    loading.value = true
    error.value = ''
    try {
      const payload = await aiApi.getAIJob(jobId.value)
      job.value = payload?.data || payload
      if (TERMINAL_STATUSES.has(String(job.value?.status || ''))) {
        stop()
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
    stop()
    await fetchOnce()
    if (!jobId.value || TERMINAL_STATUSES.has(String(job.value?.status || ''))) return
    timer = setInterval(fetchOnce, intervalMs)
  }

  onBeforeUnmount(stop)

  return {
    job,
    jobId,
    status,
    isTerminal,
    loading,
    error,
    start,
    stop,
    fetchOnce
  }
}

