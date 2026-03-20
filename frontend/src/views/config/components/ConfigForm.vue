<template>
  <div class="config-form">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      size="large"
    >
      <el-form-item label="DeepSeek API Key" prop="deepseek_api_key">
        <el-input
          v-model="form.deepseek_api_key"
          type="password"
          placeholder="请输入 DeepSeek API 密钥"
          show-password
          clearable
        >
          <template #prefix>
            <el-icon><Key /></el-icon>
          </template>
        </el-input>
        <div class="form-tips">
          获取地址：
          <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek 控制台</a>
        </div>
      </el-form-item>

      <el-form-item label="Kimi API Key" prop="kimi_api_key">
        <el-input
          v-model="form.kimi_api_key"
          type="password"
          placeholder="请输入 Kimi API 密钥"
          show-password
          clearable
        >
          <template #prefix>
            <el-icon><Key /></el-icon>
          </template>
        </el-input>
        <div class="form-tips">
          获取地址：
          <a href="https://platform.moonshot.cn/console/api-keys" target="_blank">Kimi 控制台</a>
        </div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="loading" @click="handleSave">保存配置</el-button>
        <el-button :loading="testing" @click="handleTest">测试连接</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <div v-if="testResults" class="test-results">
      <h4>连接测试结果：</h4>
      <div class="result-item">
        <span class="label">DeepSeek：</span>
        <span :class="['status', testResults.deepseek.success ? 'success' : 'error']">
          {{ testResults.deepseek.success ? '成功' : '失败' }}
          {{ testResults.deepseek.message }}
        </span>
      </div>
      <div class="result-item">
        <span class="label">Kimi：</span>
        <span :class="['status', testResults.kimi.success ? 'success' : 'error']">
          {{ testResults.kimi.success ? '成功' : '失败' }}
          {{ testResults.kimi.message }}
        </span>
      </div>
    </div>

    <div v-if="error" class="error-message">
      <el-alert
        :title="error"
        type="error"
        show-icon
        closable
        @close="clearError"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Key } from '@element-plus/icons-vue'
import { useConfigStore } from '@/stores/config'

const props = defineProps({
  initialConfig: {
    type: Object,
    default: () => ({
      deepseek_api_key: '',
      kimi_api_key: ''
    })
  }
})

const emit = defineEmits(['saved', 'tested'])

const configStore = useConfigStore()
const formRef = ref()
const loading = ref(false)
const testing = ref(false)
const error = ref('')
const testResults = ref(null)

const form = reactive({
  deepseek_api_key: '',
  kimi_api_key: ''
})

const rules = reactive({
  deepseek_api_key: [
    {
      validator: (rule, value, callback) => {
        if (!value && !form.kimi_api_key) {
          callback(new Error('至少需要配置一个 API 密钥'))
        } else if (value && value.length < 20) {
          callback(new Error('API 密钥长度至少 20 位'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  kimi_api_key: [
    {
      validator: (rule, value, callback) => {
        if (!value && !form.deepseek_api_key) {
          callback(new Error('至少需要配置一个 API 密钥'))
        } else if (value && value.length < 20) {
          callback(new Error('API 密钥长度至少 20 位'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
})

const clearError = () => {
  error.value = ''
  configStore.clearError()
}

const handleSave = async () => {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    loading.value = true
    error.value = ''

    await configStore.saveConfig({
      deepseek_api_key: form.deepseek_api_key.trim(),
      kimi_api_key: form.kimi_api_key.trim()
    })

    ElMessage.success('配置保存成功')
    emit('saved')
  } catch (err) {
    error.value = err.message
    ElMessage.error(`保存失败: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const handleTest = async () => {
  try {
    testing.value = true
    error.value = ''
    testResults.value = null

    const results = await configStore.testConfig({
      deepseek_api_key: form.deepseek_api_key.trim(),
      kimi_api_key: form.kimi_api_key.trim()
    })

    testResults.value = results
    emit('tested', results)

    if (results.deepseek.success || results.kimi.success) {
      ElMessage.success('连接测试完成')
    } else {
      ElMessage.warning('连接测试完成，但未发现有效连接')
    }
  } catch (err) {
    error.value = err.message
    ElMessage.error(`测试失败: ${err.message}`)
  } finally {
    testing.value = false
  }
}

const handleReset = () => {
  formRef.value?.resetFields()
  form.deepseek_api_key = props.initialConfig.deepseek_api_key
  form.kimi_api_key = props.initialConfig.kimi_api_key
  testResults.value = null
  error.value = ''
  clearError()
}

onMounted(() => {
  form.deepseek_api_key = props.initialConfig.deepseek_api_key
  form.kimi_api_key = props.initialConfig.kimi_api_key
})

watch(
  () => configStore.error,
  (newError) => {
    if (newError) {
      error.value = newError
    }
  }
)
</script>

<style scoped>
.config-form {
  max-width: 600px;
  margin: 0 auto;
}

.form-tips {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.form-tips a {
  color: #409eff;
  text-decoration: none;
}

.form-tips a:hover {
  text-decoration: underline;
}

.test-results {
  margin-top: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;
}

.test-results h4 {
  margin: 0 0 12px 0;
  color: #303133;
}

.result-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.label {
  min-width: 80px;
  font-weight: 500;
}

.status {
  font-size: 14px;
}

.status.success {
  color: #67c23a;
}

.status.error {
  color: #f56c6c;
}

.error-message {
  margin-top: 16px;
}
</style>
