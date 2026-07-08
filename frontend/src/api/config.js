/**
 * 配置 API 客户端模块
 *
 * 负责读取、保存和测试模型服务配置。
 */

import axios from 'axios'

const isDev = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV
const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:'
const queryPort = (() => {
  try {
    const params = new URLSearchParams(window.location.search || '')
    return params.get('backend_port')
  } catch (error) {
    return null
  }
})()
const electronPort = queryPort || '9527'

const API_BASE_URL = isDev || isFileProtocol
  ? `http://127.0.0.1:${electronPort}`
  : window.location.origin

class ConfigAPI {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.client.interceptors.request.use(
      (config) => {
        console.log(`[ConfigAPI] ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        console.error('[ConfigAPI] 请求错误:', error)
        return Promise.reject(error)
      }
    )

    this.client.interceptors.response.use(
      (response) => response.data,
      (error) => {
        console.error('[ConfigAPI] 响应错误:', error)

        if (error.response) {
          const detail = error.response.data?.detail
          const message = this._resolveErrorMessage(detail, error.response.statusText)
          throw new Error(`服务器错误 (${error.response.status}): ${message}`)
        }
        if (error.request) {
          throw new Error('网络连接失败,请检查服务器是否运行。')
        }
        throw new Error(`请求配置错误: ${error.message}`)
      }
    )
  }

  _formatValidationErrors(detail) {
    if (!Array.isArray(detail)) {
      return ''
    }
    const lines = detail
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return ''
        }
        const loc = Array.isArray(item.loc) ? item.loc.filter(Boolean).join('.') : ''
        const msg = item.msg || item.message || ''
        if (!loc && !msg) {
          return ''
        }
        return loc ? `${loc}: ${msg}` : msg
      })
      .filter(Boolean)
    if (!lines.length) {
      return ''
    }
    return `参数校验失败:${lines.join(';')}`
  }

  _resolveErrorMessage(detail, fallback = '请求失败') {
    if (Array.isArray(detail)) {
      const formatted = this._formatValidationErrors(detail)
      if (formatted) {
        return formatted
      }
    }
    if (detail && typeof detail === 'object') {
      return detail.user_message || detail.message || JSON.stringify(detail)
    }
    return detail || fallback
  }

  async getLLMConfig() {
    try {
      return await this.client.get('/api/config/llm')
    } catch (error) {
      console.error('获取配置失败:', error)
      throw error
    }
  }

  async updateLLMConfig(config) {
    try {
      const { deepseek_api_key, kimi_api_key } = config

      if (!deepseek_api_key && !kimi_api_key) {
        throw new Error('至少需要配置一个 API Key。')
      }

      return await this.client.post('/api/config/llm', {
        deepseek_api_key: deepseek_api_key || '',
        kimi_api_key: kimi_api_key || ''
      })
    } catch (error) {
      console.error('更新配置失败:', error)
      throw error
    }
  }

  async testLLMConfig(config) {
    try {
      const { deepseek_api_key, kimi_api_key } = config

      return await this.client.post('/api/config/llm/test', {
        deepseek_api_key: deepseek_api_key || '',
        kimi_api_key: kimi_api_key || ''
      })
    } catch (error) {
      console.error('测试配置失败:', error)
      throw error
    }
  }

  async deleteLLMConfig() {
    try {
      return await this.client.delete('/api/config/llm')
    } catch (error) {
      console.error('删除配置失败:', error)
      throw error
    }
  }

  async checkConfigExists() {
    try {
      const response = await this.client.get('/api/config/llm/exists')
      return response.exists
    } catch (error) {
      console.error('检查配置失败:', error)
      return false
    }
  }

  validateAPIKeyFormat(apiKey) {
    if (!apiKey) {
      return true
    }

    if (apiKey.length < 20 || apiKey.length > 100) {
      return false
    }

    const hasLetter = /[a-zA-Z]/.test(apiKey)
    const hasDigit = /\d/.test(apiKey)

    return hasLetter && hasDigit
  }

  async getConfigStatus() {
    try {
      const config = await this.getLLMConfig()
      const exists = await this.checkConfigExists()

      return {
        exists,
        hasValidConfig: config.has_config,
        deepseekConfigured: !!config.deepseek_api_key,
        kimiConfigured: !!config.kimi_api_key,
        lastUpdated: config.updated_at
      }
    } catch (error) {
      console.error('获取配置状态失败:', error)
      return {
        exists: false,
        hasValidConfig: false,
        deepseekConfigured: false,
        kimiConfigured: false,
        lastUpdated: null
      }
    }
  }
}

export const configAPI = new ConfigAPI()

export default configAPI
