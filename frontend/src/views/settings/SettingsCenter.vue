<template>
  <section class="settings-center" :class="themeClass" data-testid="settings-center">
    <header class="settings-header">
      <div>
        <h1>设置中心</h1>
        <p>在这里统一管理全局界面与 AI 配置，写作台不再承载全局设置。</p>
      </div>
    </header>

    <div class="settings-grid">
      <article class="settings-card">
        <h2>界面与阅读设置</h2>
        <p class="settings-tip">界面主题作用于整个应用，所有主功能区保持一致。</p>

        <div class="field-grid">
          <label class="field">
            <span>界面主题(全局)</span>
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

      <article class="settings-card settings-card--wide" data-test="writing-assistant-settings">
        <h2>写作助手</h2>
        <p class="settings-tip">只打开你想用的辅助功能。关闭后不会删除已经写好的新稿或资料。</p>

        <p v-if="featureCapabilityStore.loading" class="settings-tip" role="status">正在加载写作助手...</p>
        <p v-else-if="featureCapabilityStore.errorMessage" class="error-text" role="alert">
          {{ featureCapabilityStore.errorMessage }}
        </p>

        <template v-else>
          <section v-if="featureCapabilityStore.availableItems.length" class="assistant-group">
            <h3>可以使用</h3>
            <div
              v-for="item in featureCapabilityStore.availableItems"
              :key="item.feature_key"
              class="assistant-row"
            >
              <div>
                <strong>{{ item.label }}</strong>
                <p>{{ item.description }}</p>
              </div>
              <label class="assistant-switch">
                <span class="sr-only">{{ item.effective_enabled ? '关闭' : '开启' }}{{ item.label }}</span>
                <input
                  :checked="item.user_enabled"
                  type="checkbox"
                  :disabled="!item.configurable || featureCapabilityStore.savingFeatureKey === item.feature_key"
                  @change="handleFeatureToggle(item, $event.target.checked)"
                />
              </label>
            </div>
          </section>

          <details v-if="featureCapabilityStore.experimentalItems.length" class="assistant-group">
            <summary>实验功能</summary>
            <div
              v-for="item in featureCapabilityStore.experimentalItems"
              :key="item.feature_key"
              class="assistant-row"
            >
              <div>
                <strong>{{ item.label }} <small>实验功能</small></strong>
                <p>{{ item.description }}</p>
              </div>
              <label class="assistant-switch">
                <span class="sr-only">{{ item.effective_enabled ? '关闭' : '开启' }}{{ item.label }}</span>
                <input
                  :checked="item.user_enabled"
                  type="checkbox"
                  :disabled="!item.configurable || featureCapabilityStore.savingFeatureKey === item.feature_key"
                  @change="handleFeatureToggle(item, $event.target.checked)"
                />
              </label>
            </div>
          </details>

          <details v-if="featureCapabilityStore.unavailableItems.length" class="assistant-group">
            <summary>尚未开放</summary>
            <div
              v-for="item in featureCapabilityStore.unavailableItems"
              :key="item.feature_key"
              class="assistant-row assistant-row--disabled"
            >
              <div>
                <strong>{{ item.label }}</strong>
                <p>{{ item.description }}</p>
              </div>
              <span class="assistant-unavailable">尚未开放</span>
            </div>
          </details>

          <p v-if="featureCapabilityStore.noticeMessage" class="save-message" aria-live="polite">
            {{ featureCapabilityStore.noticeMessage }}
          </p>
          <p v-if="featureCapabilityStore.errorMessage" class="error-text" role="alert">
            {{ featureCapabilityStore.errorMessage }}
          </p>
        </template>
      </article>

      <article v-if="showCostSettings" class="settings-card settings-card--wide" data-test="ai-cost-settings">
        <h2>AI 费用与预算</h2>
        <p class="settings-tip">设置后，系统会在接近上限时提醒，到达上限时保护性停下新的 AI 操作。</p>
        <div class="field-grid">
          <label class="field inline"><span>开启每月费用保护</span><input v-model="costForm.enabled" type="checkbox" /></label>
          <label class="field"><span>每月预计费用上限</span><input v-model="costForm.limit" type="number" min="0" step="0.01" /></label>
          <label class="field"><span>费用单位</span><select v-model="costForm.currency"><option value="CNY">人民币</option><option value="USD">美元</option></select></label>
        </div>
        <p v-if="!costForm.enabled" class="settings-tip">预算保护已关闭。AI 使用不会受这个上限限制。</p>
        <p class="settings-tip">预算只影响之后的操作；保存后不会自动继续任何已暂停的写作任务。</p>
        <div class="settings-actions"><button type="button" class="ink-button ink-button--primary" :disabled="costSaving" @click="saveCostBudget">保存预算</button><button v-if="costWorkId && costForm.source === 'work'" type="button" class="ink-button ink-button--ghost" :disabled="costSaving" @click="restoreDefaultBudget">改回默认设置</button></div>
        <p v-if="costMessage" class="save-message">{{ costMessage }}</p>
        <p v-if="costError" class="error-text">{{ costError }}</p>
        <details v-if="costWorkId" class="assistant-group">
          <summary>更多保护</summary>
          <div class="field-grid">
            <label class="field inline"><span>整理整本作品的 AI 用量保护</span><input v-model="initializationBudget.enabled" type="checkbox" /></label>
            <label class="field"><span>单次整理用量上限</span><input v-model="initializationBudget.limit" type="number" min="0" step="1000" /></label>
            <label class="field inline"><span>一次自动续写的 AI 用量保护</span><input v-model="autoQueueBudget.enabled" type="checkbox" /></label>
            <label class="field"><span>单次自动续写用量上限</span><input v-model="autoQueueBudget.limit" type="number" min="0" step="1000" /></label>
          </div>
          <div class="settings-actions"><button type="button" class="ink-button ink-button--ghost" :disabled="costSaving" @click="saveExtraBudget('initialization', initializationBudget)">保存整理保护</button><button type="button" class="ink-button ink-button--ghost" :disabled="costSaving" @click="saveExtraBudget('auto_queue', autoQueueBudget)">保存自动续写保护</button></div>
        </details>
        <details class="assistant-group">
          <summary>更多设置：费用估算</summary>
          <p class="settings-tip">只在系统没有这个模型的可用价格时手填。不要猜价格；找不到可靠信息时，可先不用每月金额保护。</p>
          <div class="field-grid">
            <label class="field"><span>模型服务</span><input v-model="priceForm.provider_name" type="text" /></label>
            <label class="field"><span>模型名称</span><input v-model="priceForm.model_name" type="text" /></label>
            <label class="field"><span>每 100 万 AI 输入用量</span><input v-model="priceForm.input_price_per_1m" type="number" min="0" step="0.000001" /></label>
            <label class="field"><span>每 100 万 AI 输出用量</span><input v-model="priceForm.output_price_per_1m" type="number" min="0" step="0.000001" /></label>
          </div>
          <label class="field inline"><input v-model="priceForm.confirmed" type="checkbox" /><span>我已按模型服务商的官方价格说明核对</span></label>
          <p class="settings-tip">新价格只用于之后的使用，过去缺失的费用不会倒算；填错会让预计费用和金额预算不准确。</p>
          <div class="settings-actions"><button type="button" class="ink-button ink-button--ghost" :disabled="priceSaving || !priceForm.confirmed" @click="saveCostPrice">保存费用信息</button><button v-if="costWorkId && priceForm.provider_name && priceForm.model_name" type="button" class="ink-button ink-button--ghost" :disabled="priceSaving" @click="restoreDefaultPrice">此模型改回默认费用</button></div>
        </details>
      </article>

      <article class="settings-card">
        <h2>AI 设置</h2>
                <p class="settings-tip">先配置可用模型服务密钥，再完成任务模型配置。分析任务和写作任务是必填项。</p>
                <p class="settings-tip">说明：模型服务就是“大模型提供商或接入服务”，例如 DeepSeek、Kimi、OpenAI。</p>

        <div v-if="loading" class="settings-tip">正在加载 AI 设置...</div>

        <template v-else>
          <section class="provider-list">
            <h3>模型服务列表</h3>
            <div v-for="provider in providerConfigs" :key="provider.provider_name" class="provider-card">
              <div class="provider-header">
                <strong>{{ displayProviderName(provider.provider_name) }}</strong>
                <span>{{ provider.enabled ? '已启用' : '已停用' }}</span>
                                <span>密钥：{{ provider.key_configured ? '已配置' : '未配置' }}</span>
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
                  <span>模型服务密钥</span>
                  <input
                    v-model="provider.api_key"
                    type="password"
                    autocomplete="new-password"
                    placeholder="输入新密钥(不会回显旧值)"
                  />
                </label>
                <label class="field">
                  <span>服务地址(可选)</span>
                  <input v-model="provider.base_url" type="text" />
                </label>
                <label class="field">
                  <span>超时(秒)</span>
                  <input v-model.number="provider.timeout" type="number" min="1" />
                </label>
              </div>
              <div class="provider-actions">
                <button type="button" class="ink-button ink-button--ghost" @click="testProviderConnection(provider.provider_name)">测试连接</button>
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
                  <option
                    v-for="provider in providerConfigs"
                    :key="`${role}-${provider.provider_name}`"
                    :value="provider.provider_name"
                  >
                    {{ displayProviderName(provider.provider_name) }}
                  </option>
                </select>
                <input
                  v-model="settingsForm.model_role_mappings[role].model_name"
                  type="text"
                  :placeholder="`${displayRoleLabel(role)}对应模型`"
                />
              </label>
            </div>
          </section>

          <div v-if="aiSettingsBlocked" class="settings-block">
            <strong>AI 设置未完成</strong>
            <span>{{ aiSettingsBlockMessage }}</span>
          </div>

          <div class="settings-actions">
            <button type="button" class="ink-button ink-button--primary" @click="saveAISettings">保存 AI 配置</button>
            <button type="button" class="ink-button ink-button--ghost" @click="reloadAISettings">刷新</button>
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
import { useRoute } from 'vue-router'
import { usePreferenceStore } from '@/stores/preference'
import { useFeatureCapabilityStore } from '@/stores/useFeatureCapabilityStore'

const REQUIRED_SETTINGS_ROLES = ['analysis', 'planning', 'writer', 'reviewer', 'rewriter']

const preferenceStore = usePreferenceStore()
const featureCapabilityStore = useFeatureCapabilityStore()
const route = useRoute()
const showCostSettings = computed(() => true)
const costWorkId=computed(()=>String(route?.query?.work_id||''))
const costSaving = ref(false)
const costMessage = ref('')
const costError = ref('')
const costForm = reactive({ enabled: true, limit: '50', currency: 'CNY', revision: null, source: 'global' })
const initializationBudget=reactive({enabled:false,limit:'100000',revision:null})
const autoQueueBudget=reactive({enabled:false,limit:'100000',revision:null})
const priceSaving = ref(false)
const priceForm = reactive({ provider_name: '', model_name: '', input_price_per_1m: '', output_price_per_1m: '', confirmed: false, revision: null })

const reloadCostBudget = async () => {
  if (!showCostSettings.value) return
  try {
    const payload = unwrapData(await aiApi.getCostBudgets(String(route?.query?.work_id || '')))
    const monthly = (payload?.policies || []).find((item) => item.budget_type === 'monthly')
    const initialization=(payload?.policies||[]).find((item)=>item.budget_type==='initialization')
    const autoQueue=(payload?.policies||[]).find((item)=>item.budget_type==='auto_queue')
    if (monthly) Object.assign(costForm, { enabled: monthly.enabled, limit: monthly.limit, currency: monthly.currency || 'CNY', revision: monthly.revision, source: monthly.source || (costWorkId.value ? 'work' : 'global') })
    if(initialization) Object.assign(initializationBudget,{enabled:initialization.enabled,limit:initialization.limit,revision:initialization.revision})
    if(autoQueue) Object.assign(autoQueueBudget,{enabled:autoQueue.enabled,limit:autoQueue.limit,revision:autoQueue.revision})
  } catch (error) { costError.value = String(error?.userMessage || '预算设置暂时没有加载出来。') }
}

const saveCostBudget = async () => {
  if (!costForm.enabled && !window.confirm('关闭预算保护后，AI 功能将不再受这个上限限制，可能产生更多费用。确定要关闭吗？')) return
  costSaving.value = true; costMessage.value = ''; costError.value = ''
  try {
    const response = unwrapData(await aiApi.updateCostBudget({
      work_id: String(route?.query?.work_id || ''), budget_type: 'monthly', enabled: costForm.enabled,
      limit: String(costForm.limit), currency: costForm.currency, alert_threshold: '0.8', expected_revision: costForm.revision,
      caller_type: 'user_action', user_action: true, user_id: 'local-author',
      idempotency_key: `budget-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      confirm_budget_change: true, confirm_disable: !costForm.enabled
    }))
    const policy = response?.policy || {}; costForm.revision = policy.revision ?? costForm.revision
    costMessage.value = response?.message || '预算已更新。请回到刚才的 AI 功能，由你确认后继续。'
  } catch (error) { costError.value = String(error?.userMessage || '预算没有保存成功，原来的设置还在。') }
  finally { costSaving.value = false }
}

const restoreDefaultBudget = async () => {
  costSaving.value = true; costMessage.value = ''; costError.value = ''
  try {
    await aiApi.updateCostBudget({ work_id: costWorkId.value, budget_type: 'monthly', enabled: costForm.enabled, limit: String(costForm.limit), currency: costForm.currency, alert_threshold: '0.8', expected_revision: costForm.revision, inherit_global: true, caller_type: 'user_action', user_action: true, user_id: 'local-author', idempotency_key: `budget-default-${Date.now()}`, confirm_budget_change: true, confirm_disable: true })
    costMessage.value = '已改回默认预算设置。'
    await reloadCostBudget()
  } catch (error) { costError.value = String(error?.userMessage || '没有改回默认设置，原来的设置还在。') }
  finally { costSaving.value = false }
}

const saveCostPrice = async () => {
  if (!priceForm.confirmed) return
  priceSaving.value = true; costMessage.value = ''; costError.value = ''
  try {
    const response = unwrapData(await aiApi.updateCostPrice({
      work_id: String(route?.query?.work_id || ''), provider_name: priceForm.provider_name, model_name: priceForm.model_name,
      enabled: true, input_price_per_1m: String(priceForm.input_price_per_1m), output_price_per_1m: String(priceForm.output_price_per_1m),
      currency: costForm.currency, expected_revision: priceForm.revision, caller_type: 'user_action', user_action: true, user_id: 'local-author',
      idempotency_key: `price-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, confirm_price_change: true, confirm_manual_price_source: true
    }))
    priceForm.revision = response?.policy?.revision ?? priceForm.revision; costMessage.value = response?.message || '费用信息已保存。'
  } catch (error) { costError.value = String(error?.userMessage || '费用信息没有保存成功，原来的设置还在。') }
  finally { priceSaving.value = false }
}

const restoreDefaultPrice = async () => {
  priceSaving.value = true; costMessage.value = ''; costError.value = ''
  try {
    await aiApi.updateCostPrice({ work_id: costWorkId.value, provider_name: priceForm.provider_name, model_name: priceForm.model_name, enabled: true, input_price_per_1m: String(priceForm.input_price_per_1m || 0), output_price_per_1m: String(priceForm.output_price_per_1m || 0), currency: costForm.currency, expected_revision: priceForm.revision, inherit_global: true, caller_type: 'user_action', user_action: true, user_id: 'local-author', idempotency_key: `price-default-${Date.now()}`, confirm_price_change: true, confirm_manual_price_source: true })
    costMessage.value = '这个模型已改回默认费用设置。'
  } catch (error) { costError.value = String(error?.userMessage || '没有改回默认费用，原来的设置还在。') }
  finally { priceSaving.value = false }
}

const saveExtraBudget=async(budget_type,form)=>{
  costSaving.value=true;costMessage.value='';costError.value=''
  try{
    const response=unwrapData(await aiApi.updateCostBudget({work_id:String(route?.query?.work_id||''),budget_type,enabled:form.enabled,limit:String(form.limit),currency:'',alert_threshold:'0.8',expected_revision:form.revision,caller_type:'user_action',user_action:true,user_id:'local-author',idempotency_key:`budget-${budget_type}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,confirm_budget_change:true,confirm_disable:!form.enabled}));form.revision=response?.policy?.revision??form.revision
    costMessage.value='保护已保存。已暂停的任务不会自动继续。'
  }catch(error){costError.value=String(error?.userMessage||'更多保护没有保存成功，原来的设置还在。')}
  finally{costSaving.value=false}
}

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
  model_role_mappings: Object.fromEntries(REQUIRED_SETTINGS_ROLES.map((role) => [role, { provider_name: '', model_name: '' }]))
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
  fake: '测试占位服务(不可正式使用)'
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

const handleFeatureToggle = async (item, enabled) => {
  await featureCapabilityStore.setEnabled(item.feature_key, enabled)
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
    return '请至少配置一个已启用模型服务的密钥。'
  }
  for (const role of ['analysis', 'writer']) {
    const mapping = settingsForm.model_role_mappings[role]
    if (!mapping || !String(mapping.provider_name || '').trim() || !String(mapping.model_name || '').trim()) {
      return `请完成“${displayRoleLabel(role)}”并选择可用模型服务。`
    }
    const provider = providerConfigs.value.find((item) => item.provider_name === mapping.provider_name)
    if (!provider || !provider.enabled || !(provider.key_configured || String(provider.api_key || '').trim())) {
      return `“${displayRoleLabel(role)}”选择的模型服务不可用，请检查启用状态和密钥。`
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
    enabled: Boolean(provider.enabled),
    default_model: String(provider.default_model || '').trim(),
    api_key: String(provider.api_key || '').trim() || undefined,
    timeout: Number(provider.timeout || 30),
    base_url: String(provider.base_url || '').trim() || undefined
  })),
  model_role_mappings: Object.fromEntries(REQUIRED_SETTINGS_ROLES.map((role) => {
    const item = settingsForm.model_role_mappings[role] || {}
    return [role, {
      provider_name: String(item.provider_name || '').trim(),
      model_name: String(item.model_name || '').trim()
    }]
  }))
})

const saveAISettings = async () => {
  aiSaveMessage.value = ''
  aiErrorMessage.value = ''
  try {
    const payload = buildSettingsPayload()
    const response = unwrapData(await aiApi.updateAISettings(payload))
    resetSettingsForm(response)
    aiSaveMessage.value = 'AI 配置已保存。'
  } catch (error) {
    aiErrorMessage.value = String(error?.safe_message || error?.userMessage || error?.message || '保存 AI 配置失败')
  }
}

const testProviderConnection = async (providerName) => {
  aiSaveMessage.value = ''
  aiErrorMessage.value = ''
  const provider = providerConfigs.value.find((item) => item.provider_name === providerName)
  if (!provider) return
  try {
    const payload = {
      caller_type: 'user_action',
      user_action: true,
      idempotency_key: buildIdempotencyKey('provider_test'),
      provider_name: provider.provider_name,
      api_key: String(provider.api_key || '').trim() || undefined,
      timeout: Number(provider.timeout || 30),
      base_url: String(provider.base_url || '').trim() || undefined,
      default_model: String(provider.default_model || '').trim() || undefined
    }
    const result = unwrapData(await aiApi.testProvider(provider.provider_name, payload))
    provider.last_test_status = result.status || 'unknown'
    provider.last_test_error_message = result.error_message || ''
    if (result.status === 'ok' || result.status === 'passed') {
      aiSaveMessage.value = `${displayProviderName(provider.provider_name)} 测试成功。`
    }
  } catch (error) {
    provider.last_test_status = 'failed'
    provider.last_test_error_message = String(error?.safe_message || error?.userMessage || error?.message || '测试失败')
  }
}

onMounted(async () => {
  preferenceStore.hydrate()
  generalForm.appTheme = preferenceStore.appTheme
  generalForm.fontFamily = preferenceStore.fontFamily
  generalForm.fontSize = preferenceStore.fontSize
  generalForm.lineHeight = preferenceStore.lineHeight
  await Promise.all([reloadAISettings(), featureCapabilityStore.refresh(), reloadCostBudget()])
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

.settings-center--dark,
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

.settings-card--wide {
  grid-column: 1 / -1;
}

.assistant-group {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.assistant-group summary {
  min-height: 44px;
  display: flex;
  align-items: center;
  font-weight: 600;
  cursor: pointer;
}

.assistant-row {
  min-height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 16px;
  border: 1px solid var(--settings-border);
  border-radius: var(--ink-radius-md);
  background: var(--settings-card-bg);
}

.assistant-row p {
  margin: 5px 0 0;
  color: var(--settings-muted);
}

.assistant-row small,
.assistant-unavailable {
  color: var(--settings-muted);
  font-weight: 500;
}

.assistant-row--disabled {
  opacity: 0.72;
}

.assistant-switch input {
  width: 22px;
  height: 22px;
  cursor: pointer;
}

.assistant-switch input:disabled {
  cursor: not-allowed;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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
  min-width: 96px;
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
