import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api'
import { setP2FeatureCapabilities } from '@/config/p2FeatureFlags'


const unwrapData = (payload) => payload?.data ?? payload ?? {}
const buildIdempotencyKey = (featureKey) => (
  `feature_preference_${featureKey}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
)

export const useFeatureCapabilityStore = defineStore('featureCapabilities', () => {
  const capabilities = ref([])
  const loading = ref(false)
  const savingFeatureKey = ref('')
  const errorMessage = ref('')
  const noticeMessage = ref('')

  const availableItems = computed(() => capabilities.value.filter((item) => item.release_level === 'available'))
  const experimentalItems = computed(() => capabilities.value.filter((item) => item.release_level === 'experimental'))
  const unavailableItems = computed(() => capabilities.value.filter((item) => item.release_level === 'unavailable'))

  const refresh = async () => {
    loading.value = true
    errorMessage.value = ''
    try {
      const payload = unwrapData(await aiApi.getFeatureCapabilities())
      capabilities.value = Array.isArray(payload.capabilities) ? payload.capabilities : []
      setP2FeatureCapabilities(capabilities.value)
    } catch (error) {
      capabilities.value = []
      errorMessage.value = '写作助手状态暂时没有加载出来，基础写作不受影响。'
    } finally {
      loading.value = false
    }
  }

  const setEnabled = async (featureKey, enabled) => {
    const current = capabilities.value.find((item) => item.feature_key === featureKey)
    if (!current?.configurable) return null
    savingFeatureKey.value = featureKey
    errorMessage.value = ''
    noticeMessage.value = ''
    try {
      const payload = unwrapData(await aiApi.updateFeaturePreference(featureKey, {
        enabled: Boolean(enabled),
        caller_type: 'user_action',
        user_action: true,
        idempotency_key: buildIdempotencyKey(featureKey)
      }))
      const updated = payload.capability
      capabilities.value = capabilities.value.map((item) => (
        item.feature_key === featureKey ? updated : item
      ))
      setP2FeatureCapabilities(capabilities.value)
      noticeMessage.value = `${updated.label}已${updated.effective_enabled ? '开启' : '关闭'}。`
      return updated
    } catch (error) {
      errorMessage.value = '没有保存成功，原来的设置还在。'
      return null
    } finally {
      savingFeatureKey.value = ''
    }
  }

  return {
    capabilities,
    loading,
    savingFeatureKey,
    errorMessage,
    noticeMessage,
    availableItems,
    experimentalItems,
    unavailableItems,
    refresh,
    setEnabled
  }
})
