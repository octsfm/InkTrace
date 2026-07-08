import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import SettingsCenter from '../SettingsCenter.vue'
import { usePreferenceStore } from '@/stores/preference'

const getAISettings = vi.fn()
const updateAISettings = vi.fn()
const testProvider = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    getAISettings: (...args) => getAISettings(...args),
    updateAISettings: (...args) => updateAISettings(...args),
    testProvider: (...args) => testProvider(...args)
  }
}))

function buildSettingsPayload(overrides = {}) {
  return {
    provider_configs: [
      {
        provider_name: 'deepseek',
        enabled: true,
        default_model: 'deepseek-chat',
        api_key_masked: 'sk-***1234',
        key_configured: true,
        timeout: 30,
        base_url: 'https://api.deepseek.com',
        last_test_status: 'not_tested',
        last_test_error_message: ''
      },
      {
        provider_name: 'fake',
        enabled: false,
        default_model: '',
        api_key_masked: '',
        key_configured: false,
        timeout: 30,
        base_url: '',
        last_test_status: '',
        last_test_error_message: ''
      }
    ],
    model_role_mappings: {
      analysis: { provider_name: 'deepseek', model_name: 'deepseek-chat' },
      planning: { provider_name: 'deepseek', model_name: 'deepseek-chat' },
      writer: { provider_name: 'deepseek', model_name: 'deepseek-writer' },
      reviewer: { provider_name: 'deepseek', model_name: 'deepseek-reviewer' },
      rewriter: { provider_name: 'deepseek', model_name: 'deepseek-rewriter' }
    },
    ...overrides
  }
}

async function mountPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(SettingsCenter, {
    global: {
      plugins: [pinia]
    }
  })
  await flushPromises()
  return { wrapper, preferenceStore: usePreferenceStore() }
}

describe('SettingsCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-app-theme')
    getAISettings.mockResolvedValue({ data: buildSettingsPayload() })
    updateAISettings.mockImplementation(async (payload) => ({
      data: buildSettingsPayload({
        provider_configs: payload.provider_configs.map((provider) => ({
          ...provider,
          api_key_masked: provider.api_key ? 'sk-***new' : '',
          key_configured: Boolean(provider.api_key) || provider.provider_name === 'deepseek',
          last_test_status: 'not_tested',
          last_test_error_message: ''
        })),
        model_role_mappings: payload.model_role_mappings
      })
    }))
    testProvider.mockResolvedValue({ data: { status: 'ok', error_message: '' } })
  })

  it('加载后展示模型服务与脱敏状态', async () => {
    const { wrapper } = await mountPage()

    expect(getAISettings).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('设置中心')
    expect(wrapper.text()).toContain('AI 设置')
    expect(wrapper.text()).toContain('deepseek')
    expect(wrapper.text()).toContain('已启用')
    expect(wrapper.text()).toContain('Key：已配置')
    expect(wrapper.text()).toContain('sk-***1234')
  })

  it('未完成 analysis 或 writer 配置时展示阻断提示', async () => {
    getAISettings.mockResolvedValueOnce({
      data: buildSettingsPayload({
        model_role_mappings: {
          analysis: { provider_name: '', model_name: '' },
          planning: { provider_name: 'deepseek', model_name: 'deepseek-chat' },
          writer: { provider_name: '', model_name: '' },
          reviewer: { provider_name: 'deepseek', model_name: 'deepseek-reviewer' },
          rewriter: { provider_name: 'deepseek', model_name: 'deepseek-rewriter' }
        }
      })
    })

    const { wrapper } = await mountPage()

    expect(wrapper.text()).toContain('AI 设置未完成')
    expect(wrapper.text()).toContain('请完成“分析任务模型”并选择可用模型服务。')
  })

  it('保存 AI 配置时透传 caller_type、user_action 与幂等键', async () => {
    const { wrapper } = await mountPage()

    const providerCard = wrapper.findAll('.provider-card')[0]
    const providerTextInputs = providerCard.findAll('input[type="text"]')
    const keyInputs = providerCard.findAll('input[type="password"]')
    const roleFields = wrapper.findAll('.role-mappings .field')

    await providerTextInputs[0].setValue('deepseek-reasoner')
    await keyInputs[0].setValue('sk-live-123456')
    await roleFields[0].find('select').setValue('deepseek')
    await roleFields[0].find('input[type="text"]').setValue('deepseek-chat')
    await roleFields[2].find('select').setValue('deepseek')
    await roleFields[2].find('input[type="text"]').setValue('deepseek-writer')

    const saveButton = wrapper.findAll('button').find((node) => node.text().includes('保存 AI 配置'))
    expect(saveButton).toBeTruthy()
    await saveButton.trigger('click')
    await flushPromises()

    expect(updateAISettings).toHaveBeenCalledTimes(1)
    const payload = updateAISettings.mock.calls[0][0]
    expect(payload.caller_type).toBe('user_action')
    expect(payload.user_action).toBe(true)
    expect(payload.idempotency_key).toMatch(/^settings_update_/)
    expect(payload.provider_configs[0]).toMatchObject({
      provider_name: 'deepseek',
      enabled: true,
      default_model: 'deepseek-reasoner',
      api_key: 'sk-live-123456'
    })
    expect(payload.model_role_mappings.analysis).toMatchObject({
      provider_name: 'deepseek',
      model_name: 'deepseek-chat'
    })
    expect(payload.model_role_mappings.writer).toMatchObject({
      provider_name: 'deepseek',
      model_name: 'deepseek-writer'
    })
    expect(wrapper.text()).toContain('AI 配置已保存。')
  })

  it('测试连接使用脱敏输入并反馈成功状态', async () => {
    const { wrapper } = await mountPage()

    const keyInputs = wrapper.findAll('input[type="password"]')
    await keyInputs[0].setValue('sk-test-connection')

    const testButton = wrapper.findAll('button').find((node) => node.text().includes('测试连接'))
    expect(testButton).toBeTruthy()
    await testButton.trigger('click')
    await flushPromises()

    expect(testProvider).toHaveBeenCalledTimes(1)
    const [providerName, payload] = testProvider.mock.calls[0]
    expect(providerName).toBe('deepseek')
    expect(payload).toMatchObject({
      caller_type: 'user_action',
      user_action: true,
      provider_name: 'deepseek',
      api_key: 'sk-test-connection'
    })
    expect(payload.idempotency_key).toMatch(/^provider_test_/)
    expect(wrapper.text()).toContain('测试状态：连接成功')
    expect(wrapper.text()).toContain('deepseek 测试成功。')
  })

  it('保存通用设置会同步全局主题到偏好仓库', async () => {
    const { wrapper, preferenceStore } = await mountPage()

    const themeSelect = wrapper.findAll('select')[0]
    await themeSelect.setValue('dark')
    await flushPromises()

    expect(preferenceStore.appTheme).toBe('dark')
    expect(preferenceStore.editorTheme).toBe('dark')
    expect(document.documentElement.getAttribute('data-app-theme')).toBe('dark')
    expect(wrapper.text()).toContain('通用设置已保存。')
  })
})
