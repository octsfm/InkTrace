<template>
  <section class="settings-center" :class="themeClass" data-testid="settings-center">
    <header class="settings-header">
      <div>
        <h1>设置中心</h1>
        <p>在这里统一配置全局界面与 AI 能力，写作台不再承载全局设置。</p>
      </div>
    </header>

    <div class="settings-grid">
      <article class="settings-card">
        <h2>界面与阅读设置</h2>
        <p class="settings-tip">界面主题作用于整个应用，所有主功能区保持一致，不再单独设置编辑器主题。</p>

        <div class="field-grid">
          <label class="field">
            <span>界面主题（全局）</span>
            <select v-model="generalForm.appTheme" @change="saveGeneralSettings">
              <option value="light">浅色</option>
              <option value="warm">暖色</option>
              <option value="dark">深色</option>
            </select>
          </label>
          <label class="field">
            <span>编辑字体</span>
            <input v-model="generalForm.fontFamily" type="text" @blur="saveGeneralSettings" />
          </label>
          <label class="field">
            <span>编辑字号</span>
            <input v-model.number="generalForm.fontSize" type="number" min="12" max="32" @change="saveGeneralSettings" />
          </label>
          <label class="field">
            <span>编辑行高</span>
            <input v-model.number="generalForm.lineHeight" type="number" min="1.2" max="2.4" step="0.1" @change="saveGeneralSettings" />
          </label>
        </div>
        <p class="save-message">{{ generalMessage }}</p>
      </article>

      <article class="settings-card">
        <h2>AI 设置</h2>
        <p class="settings-tip">先配置可用模型服务商 Key，再完成任务模型配置。分析任务和写作任务是必填项。</p>
        <p class="settings-tip">
          说明：模型服务商是“大模型提供商或接入服务”，例如你接入的 DeepSeek、Kimi、OpenAI 等通道。
        </p>

        <div v-if="loading" class="settings-tip">正在加载 AI 设置...</div>

        <template v-else>
          <section class="provider-list">
            <h3>模型服务商列表</h3>
            <div
              v-for="provider in providerConfigs"
              :key="provider.provider_name"
              class="provider-card"
            >
              <div class="provider-header">
                <strong>{{ displayProviderName(provider.provider_name) }}</strong>
                <span>{{ provider.enabled ? '已启用' : '已停用' }}</span>
                <span>Key：{{ provider.key_configured ? '已配置' : '未配置' }}</span>
                <span v-if="provider.api_key_masked">{{ provider.api_key_masked }}</span>
              </div>
              <div class="field-grid">
                <label class="field inline">
                  <span>启用</span>
                  <input v-model="provider.enabled" type="checkbox" />
                </label>
                <label class="field">
                  <span>默认模型</span>
                  <input v-model="provider.default_model" type="text" placeholder="例如 deepseek-chat" />
                </label>
                <label class="field">
                  <span>模型服务商 Key</span>
                  <input v-model="provider.api_key" type="password" autocomplete="new-password" placeholder="输入新 Key（不回显旧值）" />
                </label>
                <label class="field">
                  <span>服务地址（可选）</span>
                  <input v-model="provider.base_url" type="text" />
                </label>
                <label class="field">
                  <span>超时（秒）</span>
                  <input v-model.number="provider.timeout" type="number" min="1" />
                </label>
              </div>
              <div class="provider-actions">
                <button type="button" @click="testProvider(provider.provider_name)">测试连接</button>
                <span v-if="provider.last_test_status">测试状态：{{ displayTestStatus(provider.last_test_status) }}</span>
                <span v-if="provider.last_test_error_message" class="error-text">{{ provider.last_test_error_message }}</span>
              </div>
            </div>
          </section>

          <section class="role-mappings">
            <h3>任务模型配置</h3>
            <div class="field-grid">
              <label v-for="role in requiredSettingsRoles" :key="role" class="field">
                <span>{{ displayRoleLabel(role) }}</span>
                <select v-model="settingsForm.model_role_mappings[role].provider_name">
                  <option value="">请选择模型服务</option>
                  <option v-for="provider in providerConfigs" :key="`${role}-${provider.provider_name}`" :value="provider.provider_name">
                    {{ displayProviderName(provider.provider_name) }}
                  </option>
                </select>
                <input v-model="settingsForm.model_role_mappings[role].model_name" type="text" :placeholder="`${displayRoleLabel(role)}对应模型`" />
              </label>
            </div>
          </section>

          <div v-if="aiSettingsBlocked" class="settings-block">
            <strong>AI 设置未完成</strong>
            <span>{{ aiSettingsBlockMessage }}</span>
          </div>

          <div class="settings-actions">
            <button type="button" @click="saveAISettings">保存 AI 配置</button>
            <button type="button" @click="reloadAISettings">刷新</button>
          </div>
          <p v-if="aiSaveMessage" class="save-message">{{ aiSaveMessage }}</p>
          <p v-if="aiErrorMessage" class="error-text">{{ aiErrorMessage }}</p>
        </template>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { aiApi } from '@/api'
import { usePreferenceStore } from '@/stores/preference'

const REQUIRED_SETTINGS_ROLES = ['analysis', 'planning', 'writer', 'reviewer', 'rewriter']

const preferenceStore = usePreferenceStore()

const generalForm = reactive({
  appTheme: preferenceStore.appTheme || 'light',
  fontFamily: preferenceStore.fontFamily,
  fontSize: preferenceStore.fontSize,
  lineHeight: preferenceStore.lineHeight
})
const generalMessage = ref('通用设置已加载。')

const loading = ref(false)
const settingsForm = reactive({
  provider_configs: [],
  model_role_mappings: Object.fromEntries(
    REQUIRED_SETTINGS_ROLES.map((role) => [role, { provider_name: '', model_name: '' }])
  )
})
const aiSaveMessage = ref('')
const aiErrorMessage = ref('')

const requiredSettingsRoles = REQUIRED_SETTINGS_ROLES
const themeClass = computed(() => `settings-center--${String(preferenceStore.appTheme || 'light')}`)
const providerConfigs = computed(() => settingsForm.provider_configs || [])
const roleLabelMap = {
  analysis: '分析任务模型',
  planning: '规划任务模型',
  writer: '写作任务模型',
  reviewer: '审阅任务模型',
  rewriter: '重写任务模型'
}
const providerNameAliasMap = {
  fake: '测试占位服务（不可正式使用）'
}
const testStatusLabelMap = {
  ok: '连接成功',
  passed: '通过',
  failed: '失败',
  unknown: '未知',
  not_tested: '未测试'
}

const buildIdempotencyKey = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
const unwrapData = (payload) => payload?.data ?? payload ?? {}
const displayTestStatus = (value) => testStatusLabelMap[String(value || '').trim()] || String(value || '未知')
const displayRoleLabel = (role) => roleLabelMap[String(role || '').trim()] || String(role || '未命名角色')
const displayProviderName = (providerName) => {
  const key = String(providerName || '').trim()
  if (!key) return '未命名模型服务'
  return providerNameAliasMap[key] || key
}

const saveGeneralSettings = () => {
  preferenceStore.updateWritingPreferences({
    appTheme: generalForm.appTheme,
    fontFamily: generalForm.fontFamily,
    fontSize: generalForm.fontSize,
    lineHeight: generalForm.lineHeight
  })
  generalMessage.value = '通用设置已保存。'
}

const resetSettingsForm = (payload) => {
  const nextSettings = payload || { provider_configs: [], model_role_mappings: {} }
  const nextProviders = Array.isArray(nextSettings.provider_configs)
    ? nextSettings.provider_configs.map((provider) => ({
      provider_name: provider.provider_name || '',
      enabled: provider.enabled !== false,
      default_model: provider.default_model || '',
      api_key: '',
      api_key_masked: provider.api_key_masked || '',
      key_configured: Boolean(provider.key_configured),
      timeout: Number(provider.timeout || 30),
      base_url: provider.base_url || '',
      last_test_status: provider.last_test_status || '',
      last_test_error_message: provider.last_test_error_message || ''
    }))
    : []
  settingsForm.provider_configs.splice(0, settingsForm.provider_configs.length, ...nextProviders)

  const nextMappings = {}
  for (const role of REQUIRED_SETTINGS_ROLES) {
    const current = nextSettings.model_role_mappings?.[role] || {}
    nextMappings[role] = {
      provider_name: current.provider_name || '',
      model_name: current.model_name || ''
    }
  }
  for (const key of Object.keys(settingsForm.model_role_mappings)) delete settingsForm.model_role_mappings[key]
  Object.assign(settingsForm.model_role_mappings, nextMappings)
}

const aiSettingsBlockMessage = computed(() => {
  const enabledProviders = providerConfigs.value.filter((provider) => provider.enabled)
  if (!enabledProviders.some((provider) => provider.key_configured || String(provider.api_key || '').trim())) {
    return '请至少配置一个已启用模型服务商的 Key。'
  }
  for (const role of ['analysis', 'writer']) {
    const mapping = settingsForm.model_role_mappings[role]
    if (!mapping || !String(mapping.provider_name || '').trim() || !String(mapping.model_name || '').trim()) {
      return `请完成“${displayRoleLabel(role)}”并选择可用模型服务。`
    }
    const provider = providerConfigs.value.find((item) => item.provider_name === mapping.provider_name)
    if (!provider || !provider.enabled || !(provider.key_configured || String(provider.api_key || '').trim())) {
      return `“${displayRoleLabel(role)}”选择的模型服务不可用，请检查启用状态和 Key。`
    }
  }
  return ''
})

const aiSettingsBlocked = computed(() => Boolean(aiSettingsBlockMessage.value))

const reloadAISettings = async () => {
  loading.value = true
  aiErrorMessage.value = ''
  try {
    const payload = unwrapData(await aiApi.getAISettings())
    resetSettingsForm(payload)
  } catch (error) {
    aiErrorMessage.value = String(error?.userMessage || error?.message || '加载 AI 设置失败')
  } finally {
    loading.value = false
  }
}

const buildSettingsPayload = () => ({
  caller_type: 'user_action',
  user_action: true,
  idempotency_key: buildIdempotencyKey('settings_update'),
  provider_configs: providerConfigs.value.map((provider) => ({
    provider_name: provider.provider_name,
    enabled: provider.enabled,
    api_key: String(provider.api_key || '').trim(),
    default_model: String(provider.default_model || '').trim(),
    timeout: Number(provider.timeout || 30),
    base_url: String(provider.base_url || '').trim() || null
  })),
  model_role_mappings: Object.fromEntries(
    Object.entries(settingsForm.model_role_mappings).map(([role, mapping]) => [role, {
      provider_name: String(mapping.provider_name || '').trim(),
      model_name: String(mapping.model_name || '').trim()
    }])
  )
})

const saveAISettings = async () => {
  aiSaveMessage.value = ''
  aiErrorMessage.value = ''
  try {
    const payload = unwrapData(await aiApi.updateAISettings(buildSettingsPayload()))
    resetSettingsForm(payload)
    aiSaveMessage.value = 'AI 设置已保存。'
  } catch (error) {
    aiErrorMessage.value = String(error?.userMessage || error?.message || '保存 AI 设置失败')
  }
}

const testProvider = async (providerName) => {
  aiSaveMessage.value = ''
  aiErrorMessage.value = ''
  try {
    const payload = unwrapData(await aiApi.testProvider(providerName, {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('provider_test'),
      provider_name: providerName
    }))
    const index = settingsForm.provider_configs.findIndex((item) => item.provider_name === providerName)
    if (index >= 0) {
      const current = settingsForm.provider_configs[index]
      settingsForm.provider_configs[index] = {
        ...current,
        last_test_status: payload.test_status || payload.status || 'unknown',
        last_test_error_message: payload.error_message || ''
      }
    }
    aiSaveMessage.value = `${displayProviderName(providerName)} 测试完成。`
  } catch (error) {
    aiErrorMessage.value = String(error?.userMessage || error?.message || `${displayProviderName(providerName)} 测试失败`)
  }
}

onMounted(async () => {
  await reloadAISettings()
})
</script>

<style scoped>
.settings-center {
  --settings-page-bg: var(--ink-bg-app);
  --settings-card-bg: var(--ink-surface-1);
  --settings-border: var(--ink-border);
  --settings-border-strong: var(--ink-border-strong);
  --settings-title: var(--ink-text-primary);
  --settings-text: var(--ink-text-secondary);
  --settings-muted: var(--ink-text-muted);
  --settings-input-bg: var(--ink-surface-1);
  --settings-success: var(--ink-success-text);
  --settings-error: var(--ink-danger-text);
  --settings-warning-bg: var(--ink-warning-bg);
  --settings-warning-border: var(--ink-border-strong);
  --settings-warning-text: var(--ink-warning-text);

  max-width: 1280px;
  margin: 0 auto;
  padding: 28px 24px 40px;
  color: var(--settings-text);
  background: transparent;
}

.settings-center--dark {
  --settings-page-bg: var(--ink-bg-app);
  --settings-card-bg: var(--ink-surface-1);
  --settings-border: var(--ink-border);
  --settings-border-strong: var(--ink-border-strong);
  --settings-title: var(--ink-text-primary);
  --settings-text: var(--ink-text-secondary);
  --settings-muted: var(--ink-text-muted);
  --settings-input-bg: var(--ink-surface-1);
  --settings-success: var(--ink-success-text);
  --settings-error: var(--ink-danger-text);
  --settings-warning-bg: var(--ink-warning-bg);
  --settings-warning-border: var(--ink-border-strong);
  --settings-warning-text: var(--ink-warning-text);
}

.settings-center--warm {
  --settings-page-bg: var(--ink-bg-app);
  --settings-card-bg: var(--ink-surface-1);
  --settings-border: var(--ink-border);
  --settings-border-strong: var(--ink-border-strong);
  --settings-title: var(--ink-text-primary);
  --settings-text: var(--ink-text-secondary);
  --settings-muted: var(--ink-text-muted);
  --settings-input-bg: var(--ink-surface-1);
}

.settings-header h1 {
  margin: 0;
  font-size: 28px;
  color: var(--settings-title);
}

.settings-header p {
  margin: 8px 0 0;
  color: var(--settings-muted);
}

.settings-grid {
  margin-top: 20px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.settings-card {
  border: 1px solid var(--settings-border);
  border-radius: 16px;
  background: var(--settings-card-bg);
  padding: 16px;
}

.settings-card h2,
.provider-list h3,
.role-mappings h3 {
  color: var(--settings-title);
}

.settings-tip {
  margin: 0 0 12px;
  color: var(--settings-muted);
  font-size: 13px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--settings-text);
}

.field.inline {
  flex-direction: row;
  align-items: center;
}

.field input,
.field select {
  border: 1px solid var(--settings-border-strong);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
  color: var(--settings-title);
  background: var(--settings-input-bg);
}

.provider-list,
.role-mappings {
  margin-top: 14px;
}

.provider-card {
  border: 1px solid var(--settings-border);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: color-mix(in srgb, var(--settings-card-bg) 88%, #e2e8f0 12%);
}

.provider-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--settings-muted);
  font-size: 13px;
}

.provider-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.provider-actions button,
.settings-actions button {
  border: 1px solid var(--settings-border-strong);
  border-radius: 10px;
  background: var(--settings-input-bg);
  color: var(--settings-title);
  padding: 8px 12px;
  cursor: pointer;
}

.settings-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.settings-block {
  margin-top: 12px;
  border: 1px solid var(--settings-warning-border);
  background: var(--settings-warning-bg);
  border-radius: 12px;
  padding: 10px;
  color: var(--settings-warning-text);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.save-message {
  margin-top: 10px;
  color: var(--settings-success);
}

.error-text {
  color: var(--settings-error);
}
</style>
