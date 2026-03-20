<template>
  <div class="llm-config-page">
    <div class="page-header">
      <h1>大模型配置</h1>
      <p>配置 DeepSeek 和 Kimi API 密钥，用于 AI 小说创作</p>
    </div>

    <div v-if="configStore.configStatus.exists" class="config-status">
      <el-alert title="配置已保存" type="success" show-icon :closable="false">
        <template #description>
          <div class="status-details">
            <span v-if="configStore.configStatus.deepseekConfigured">已配置 DeepSeek</span>
            <span v-if="configStore.configStatus.kimiConfigured">已配置 Kimi</span>
            <span class="update-time">最后更新：{{ formatUpdateTime(configStore.configStatus.lastUpdated) }}</span>
          </div>
        </template>
      </el-alert>
    </div>

    <div class="config-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>API 密钥配置</span>
            <el-button
              v-if="configStore.configStatus.exists"
              type="danger"
              size="small"
              @click="handleDeleteConfig"
            >
              删除配置
            </el-button>
          </div>
        </template>

        <ConfigForm
          :initial-config="configStore.config"
          @saved="handleConfigSaved"
          @tested="handleConfigTested"
        />
      </el-card>
    </div>

    <div class="info-section">
      <el-card>
        <template #header>
          <span>配置说明</span>
        </template>

        <div class="info-content">
          <h3>配置要求</h3>
          <ul>
            <li>至少需要配置一个 API 密钥，DeepSeek 或 Kimi 均可</li>
            <li>API 密钥会加密存储，尽量保证安全性</li>
            <li>配置完成后，应用会自动使用可用模型</li>
          </ul>

          <h3>获取 API 密钥</h3>
          <ul>
            <li>
              <strong>DeepSeek：</strong>
              <a href="https://platform.deepseek.com/api_keys" target="_blank">前往 DeepSeek 控制台获取</a>
            </li>
            <li>
              <strong>Kimi：</strong>
              <a href="https://platform.moonshot.cn/console/api-keys" target="_blank">前往 Kimi 控制台获取</a>
            </li>
          </ul>

          <h3>主备模式</h3>
          <ul>
            <li>应用会优先使用 DeepSeek 作为主模型</li>
            <li>当 DeepSeek 不可用时，会自动切换到 Kimi</li>
            <li>建议同时配置两个密钥，以提高稳定性</li>
          </ul>
        </div>
      </el-card>
    </div>

    <div v-if="configStore.loading" class="loading-overlay">
      <el-spinner size="large" />
      <span>处理中...</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ConfigForm from './components/ConfigForm.vue'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()

const formatUpdateTime = (timeString) => {
  if (!timeString) return '未知'
  try {
    const date = new Date(timeString)
    return date.toLocaleString('zh-CN')
  } catch {
    return timeString
  }
}

const handleConfigSaved = () => {
  ElMessage.success('配置已保存并生效')
}

const handleConfigTested = (results) => {
  console.log('配置测试结果:', results)
}

const handleDeleteConfig = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除配置吗？删除后需要重新配置 API 密钥才能使用 AI 功能。',
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await configStore.deleteConfig()
    ElMessage.success('配置已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败: ${error.message}`)
    }
  }
}

onMounted(async () => {
  try {
    await configStore.initialize()
  } catch (error) {
    console.error('初始化配置页面失败:', error)
    ElMessage.error('加载配置失败，请刷新页面重试')
  }
})
</script>

<style scoped>
.llm-config-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.config-status {
  margin-bottom: 20px;
}

.status-details {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.status-details span {
  font-size: 13px;
}

.update-time {
  color: #909399;
  font-style: italic;
}

.config-section {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-section {
  margin-bottom: 24px;
}

.info-content h3 {
  margin: 16px 0 8px 0;
  color: #303133;
  font-size: 16px;
}

.info-content ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
}

.info-content li {
  margin-bottom: 4px;
  line-height: 1.5;
}

.info-content a {
  color: #409eff;
  text-decoration: none;
}

.info-content a:hover {
  text-decoration: underline;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}
</style>
