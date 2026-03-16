/**
 * 配置API客户端模块
 * 
 * 作者：孔利群
 */

import axios from 'axios'

const isDev = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV
const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:'

const API_BASE_URL = isDev || isFileProtocol
    ? 'http://127.0.0.1:9527'
    : window.location.origin

/**
 * 配置管理API客户端
 */
class ConfigAPI {
    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            }
        })
        
        // 请求拦截器
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
        
        // 响应拦截器
        this.client.interceptors.response.use(
            (response) => {
                return response.data
            },
            (error) => {
                console.error('[ConfigAPI] 响应错误:', error)
                
                if (error.response) {
                    // 服务器返回错误
                    const message = error.response.data?.detail || error.response.statusText
                    throw new Error(`服务器错误 (${error.response.status}): ${message}`)
                } else if (error.request) {
                    // 网络错误
                    throw new Error('网络连接失败，请检查服务器是否运行')
                } else {
                    // 其他错误
                    throw new Error(`请求配置错误: ${error.message}`)
                }
            }
        )
    }
    
    /**
     * 获取LLM配置
     */
    async getLLMConfig() {
        try {
            return await this.client.get('/api/config/llm')
        } catch (error) {
            console.error('获取配置失败:', error)
            throw error
        }
    }
    
    /**
     * 更新LLM配置
     */
    async updateLLMConfig(config) {
        try {
            const { deepseek_api_key, kimi_api_key } = config
            
            if (!deepseek_api_key && !kimi_api_key) {
                throw new Error('至少需要配置一个API密钥')
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
    
    /**
     * 测试配置连接
     */
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
    
    /**
     * 删除LLM配置
     */
    async deleteLLMConfig() {
        try {
            return await this.client.delete('/api/config/llm')
        } catch (error) {
            console.error('删除配置失败:', error)
            throw error
        }
    }
    
    /**
     * 检查配置是否存在
     */
    async checkConfigExists() {
        try {
            const response = await this.client.get('/api/config/llm/exists')
            return response.exists
        } catch (error) {
            console.error('检查配置失败:', error)
            // 如果检查失败，默认返回false
            return false
        }
    }
    
    /**
     * 验证API密钥格式
     */
    validateAPIKeyFormat(apiKey) {
        if (!apiKey) {
            return true // 空密钥是允许的
        }
        
        // 基本格式验证
        if (apiKey.length < 20 || apiKey.length > 100) {
            return false
        }
        
        // 检查是否包含字母和数字
        const hasLetter = /[a-zA-Z]/.test(apiKey)
        const hasDigit = /\d/.test(apiKey)
        
        return hasLetter && hasDigit
    }
    
    /**
     * 获取配置状态
     */
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

// 创建单例实例
export const configAPI = new ConfigAPI()

export default configAPI
