/**
 * 配置状态管理模块
 * 
 * 作者：孔利群
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import configAPI from '@/api/config'

/**
 * 配置状态管理Store
 */
export const useConfigStore = defineStore('config', () => {
    // 状态
    const config = ref({
        deepseek_api_key: '',
        kimi_api_key: ''
    })
    
    const configStatus = ref({
        exists: false,
        hasValidConfig: false,
        deepseekConfigured: false,
        kimiConfigured: false,
        lastUpdated: null
    })
    
    const loading = ref(false)
    const error = ref(null)
    
    // 计算属性
    const hasConfig = computed(() => configStatus.value.hasValidConfig)
    const isConfigured = computed(() => configStatus.value.deepseekConfigured || configStatus.value.kimiConfigured)
    const needsConfiguration = computed(() => !configStatus.value.hasValidConfig)
    
    // Actions
    
    /**
     * 加载配置
     */
    async function loadConfig() {
        loading.value = true
        error.value = null
        
        try {
            const configData = await configAPI.getLLMConfig()
            
            config.value = {
                deepseek_api_key: configData.deepseek_api_key || '',
                kimi_api_key: configData.kimi_api_key || ''
            }
            
            configStatus.value = {
                exists: configData.has_config,
                hasValidConfig: configData.has_config,
                deepseekConfigured: !!configData.deepseek_api_key,
                kimiConfigured: !!configData.kimi_api_key,
                lastUpdated: configData.updated_at
            }
            
            return configData
        } catch (err) {
            error.value = err.message
            console.error('加载配置失败:', err)
            throw err
        } finally {
            loading.value = false
        }
    }
    
    /**
     * 保存配置
     */
    async function saveConfig(newConfig) {
        loading.value = true
        error.value = null
        
        try {
            // 验证配置格式
            if (!newConfig.deepseek_api_key && !newConfig.kimi_api_key) {
                throw new Error('至少需要配置一个API密钥')
            }
            
            if (newConfig.deepseek_api_key && !configAPI.validateAPIKeyFormat(newConfig.deepseek_api_key)) {
                throw new Error('DeepSeek API密钥格式不正确')
            }
            
            if (newConfig.kimi_api_key && !configAPI.validateAPIKeyFormat(newConfig.kimi_api_key)) {
                throw new Error('Kimi API密钥格式不正确')
            }
            
            const result = await configAPI.updateLLMConfig(newConfig)
            
            // 更新本地状态
            config.value = { ...newConfig }
            await loadConfigStatus()
            
            return result
        } catch (err) {
            error.value = err.message
            console.error('保存配置失败:', err)
            throw err
        } finally {
            loading.value = false
        }
    }
    
    /**
     * 测试配置连接
     */
    async function testConfig(testConfig) {
        loading.value = true
        error.value = null
        
        try {
            const result = await configAPI.testLLMConfig(testConfig)
            return result
        } catch (err) {
            error.value = err.message
            console.error('测试配置失败:', err)
            throw err
        } finally {
            loading.value = false
        }
    }
    
    /**
     * 删除配置
     */
    async function deleteConfig() {
        loading.value = true
        error.value = null
        
        try {
            const result = await configAPI.deleteLLMConfig()
            
            // 重置本地状态
            config.value = {
                deepseek_api_key: '',
                kimi_api_key: ''
            }
            
            configStatus.value = {
                exists: false,
                hasValidConfig: false,
                deepseekConfigured: false,
                kimiConfigured: false,
                lastUpdated: null
            }
            
            return result
        } catch (err) {
            error.value = err.message
            console.error('删除配置失败:', err)
            throw err
        } finally {
            loading.value = false
        }
    }
    
    /**
     * 加载配置状态
     */
    async function loadConfigStatus() {
        try {
            const status = await configAPI.getConfigStatus()
            configStatus.value = status
            return status
        } catch (err) {
            console.error('加载配置状态失败:', err)
            // 如果加载失败，重置为默认状态
            configStatus.value = {
                exists: false,
                hasValidConfig: false,
                deepseekConfigured: false,
                kimiConfigured: false,
                lastUpdated: null
            }
            throw err
        }
    }
    
    /**
     * 清除错误
     */
    function clearError() {
        error.value = null
    }
    
    /**
     * 重置配置
     */
    function resetConfig() {
        config.value = {
            deepseek_api_key: '',
            kimi_api_key: ''
        }
        error.value = null
    }
    
    /**
     * 初始化配置状态
     */
    async function initialize() {
        try {
            await loadConfigStatus()
            
            // 如果配置存在，加载详细配置
            if (configStatus.value.hasValidConfig) {
                await loadConfig()
            }
        } catch (err) {
            console.error('初始化配置状态失败:', err)
        }
    }
    
    return {
        // 状态
        config,
        configStatus,
        loading,
        error,
        
        // 计算属性
        hasConfig,
        isConfigured,
        needsConfiguration,
        
        // Actions
        loadConfig,
        saveConfig,
        testConfig,
        deleteConfig,
        loadConfigStatus,
        clearError,
        resetConfig,
        initialize
    }
})