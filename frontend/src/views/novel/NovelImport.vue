<template>
  <div class="novel-import">
    <div class="page-header">
      <h2 class="page-title">导入小说</h2>
    </div>

    <el-card class="import-card">
      <el-form ref="formRef" :model="form" label-width="100px" :rules="rules">
        <el-form-item label="小说标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入小说标题" />
        </el-form-item>

        <el-form-item label="作者" prop="author">
          <el-input v-model="form.author" placeholder="请输入作者名" />
        </el-form-item>

        <el-form-item label="题材" prop="genre">
          <el-select v-model="form.genre" placeholder="请选择题材" style="width: 100%">
            <el-option label="玄幻" value="xuanhuan" />
            <el-option label="仙侠" value="xianxia" />
            <el-option label="都市" value="dushi" />
            <el-option label="历史" value="lishi" />
            <el-option label="科幻" value="kehuan" />
            <el-option label="武侠" value="wuxia" />
            <el-option label="奇幻" value="qihuan" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>

        <el-form-item label="目标字数" prop="target_word_count">
          <el-input-number v-model="form.target_word_count" :min="10000" :max="50000000" :step="10000" />
        </el-form-item>

        <el-form-item label="小说文件" prop="file_path">
          <el-input v-model="form.file_path" placeholder="请输入小说文件路径">
            <template #append>
              <el-button @click="selectFile">选择文件</el-button>
            </template>
          </el-input>
          <input ref="fileInput" type="file" style="display: none" accept=".txt" @change="handleFileSelect" />
          <div class="file-tip">支持 `.txt` 格式，文件将自动解析章节结构</div>
        </el-form-item>

        <el-form-item label="大纲文件">
          <el-input v-model="form.outline_path" placeholder="可选，输入大纲文件路径">
            <template #append>
              <el-button @click="selectOutline">选择文件</el-button>
            </template>
          </el-input>
          <input ref="outlineInput" type="file" style="display: none" accept=".txt" @change="handleOutlineSelect" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="importing" @click="handleImport">开始导入</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="!novelCreated" class="tip-card">
      <template #header>
        <span>导入说明</span>
      </template>
      <ul class="tip-list">
        <li>支持 TXT 格式的小说文件</li>
        <li>系统会自动识别章节标题，如“第一章”“第1章”等</li>
        <li>大纲文件可包含人物设定、故事背景等信息</li>
        <li>导入后会自动整理故事结构，并可继续创作下一章</li>
      </ul>
    </el-card>

    <el-card v-if="importing" class="progress-card">
      <template #header>
        <span>导入进度</span>
      </template>
      <el-steps :active="currentStep" finish-status="success">
        <el-step title="创建项目" />
        <el-step title="解析文件" />
        <el-step title="整理结构" />
        <el-step title="完成" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { novelApi, projectApi } from '@/api'

const router = useRouter()
const formRef = ref(null)
const fileInput = ref(null)
const outlineInput = ref(null)
const importing = ref(false)
const novelCreated = ref(false)
const createdNovelId = ref('')
const currentStep = ref(0)

const form = reactive({
  title: '',
  author: '',
  genre: '',
  target_word_count: 800000,
  file_path: '',
  outline_path: '',
  selectedFile: null,
  selectedOutline: null
})

const rules = {
  title: [{ required: true, message: '请输入小说标题', trigger: 'blur' }],
  author: [{ required: true, message: '请输入作者名', trigger: 'blur' }],
  genre: [{ required: true, message: '请选择题材', trigger: 'change' }],
  target_word_count: [{ required: true, message: '请输入目标字数', trigger: 'blur' }]
}

const selectFile = async () => {
  if (window.electronAPI) {
    const result = await window.electronAPI.selectFile({
      title: '选择小说文件',
      filters: [
        { name: '文本文件', extensions: ['txt'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    })
    if (!result.canceled && result.filePaths.length > 0) {
      form.file_path = result.filePaths[0]
    }
    return
  }
  fileInput.value?.click()
}

const selectOutline = async () => {
  if (window.electronAPI) {
    const result = await window.electronAPI.selectFile({
      title: '选择大纲文件',
      filters: [
        { name: '文本文件', extensions: ['txt'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    })
    if (!result.canceled && result.filePaths.length > 0) {
      form.outline_path = result.filePaths[0]
    }
    return
  }
  outlineInput.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  form.file_path = file.name
  form.selectedFile = file
}

const handleOutlineSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  form.outline_path = file.name
  form.selectedOutline = file
}

const handleImport = async () => {
  try {
    await formRef.value.validate()
    if (!form.file_path) {
      ElMessage.warning('请输入小说文件路径')
      return
    }

    importing.value = true
    currentStep.value = 0

    currentStep.value = 1
    let novel = null
    if (!window.electronAPI && !form.selectedFile) {
      novel = await novelApi.create({
        title: form.title,
        author: form.author,
        genre: form.genre,
        target_word_count: form.target_word_count
      })
      createdNovelId.value = novel.id
      novelCreated.value = true
    }

    currentStep.value = 2
    ElMessage.info('正在整理故事结构...')
    if (!window.electronAPI && form.selectedFile) {
      const formData = new FormData()
      formData.append('project_name', form.title)
      formData.append('genre', form.genre)
      formData.append('novel_file', form.selectedFile)
      if (form.selectedOutline) {
        formData.append('outline_file', form.selectedOutline)
      }
      formData.append('auto_organize', 'true')
      const result = await projectApi.importV2Upload(formData)
      novel = { id: result.novel_id }
    } else {
      const result = await projectApi.importV2({
        project_name: form.title,
        genre: form.genre,
        novel_file_path: form.file_path,
        outline_file_path: form.outline_path || '',
        auto_organize: true
      })
      novel = { id: result.novel_id }
    }

    currentStep.value = 3
    ElMessage.success('导入完成')
    sessionStorage.setItem(
      'inktrace_continue_hint',
      JSON.stringify({
        novelId: novel.id,
        message: '已完成分析，是否继续创作下一章？',
        defaultGoal: '第2章：承接上一章推进主线'
      })
    )

    setTimeout(() => {
      router.push(`/novel/${novel.id}`)
    }, 1000)
  } catch (error) {
    console.error('导入失败:', error)
    currentStep.value = 0
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.novel-import {
  padding: 20px;
}

.import-card {
  max-width: 800px;
  margin-bottom: 20px;
}

.input-tip {
  margin-left: 10px;
  color: #909399;
}

.file-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.tip-card {
  max-width: 800px;
}

.tip-list {
  padding-left: 20px;
  color: #606266;
  line-height: 2;
}

.progress-card {
  max-width: 800px;
  margin-top: 20px;
}
</style>
