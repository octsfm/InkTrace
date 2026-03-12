<template>
  <div class="novel-import">
    <div class="page-header">
      <h2 class="page-title">导入小说</h2>
    </div>
    
    <el-card class="import-card">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="小说标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入小说标题" />
        </el-form-item>
        
        <el-form-item label="作者" prop="author">
          <el-input v-model="form.author" placeholder="请输入作者名" />
        </el-form-item>
        
        <el-form-item label="题材" prop="genre">
          <el-select v-model="form.genre" placeholder="请选择题材">
            <el-option label="玄幻" value="玄幻" />
            <el-option label="仙侠" value="仙侠" />
            <el-option label="都市" value="都市" />
            <el-option label="历史" value="历史" />
            <el-option label="科幻" value="科幻" />
            <el-option label="现代修真" value="现代修真" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="目标字数" prop="target_word_count">
          <el-input-number v-model="form.target_word_count" :min="10000" :step="10000" />
          <span class="input-tip">字</span>
        </el-form-item>
        
        <el-divider>导入小说文件</el-divider>
        
        <el-form-item label="小说文件">
          <el-input v-model="form.file_path" placeholder="请输入小说文件路径">
            <template #append>
              <el-button @click="selectFile">选择文件</el-button>
            </template>
          </el-input>
          <div class="file-tip">
            支持 .txt 格式，文件将自动解析章节结构
          </div>
        </el-form-item>
        
        <el-form-item label="大纲文件">
          <el-input v-model="form.outline_path" placeholder="请输入大纲文件路径（可选）">
            <template #append>
              <el-button @click="selectOutline">选择文件</el-button>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleImport" :loading="importing">
            <el-icon><Upload /></el-icon>
            开始导入
          </el-button>
          <el-button @click="$router.push('/novels')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card class="tip-card" v-if="!novelCreated">
      <template #header>
        <span>导入说明</span>
      </template>
      <ul class="tip-list">
        <li>支持 TXT 格式的小说文件</li>
        <li>系统会自动识别章节标题（如"第一章"、"第1章"等）</li>
        <li>大纲文件可包含人物设定、故事背景等信息</li>
        <li>导入后可进行文风分析和续写</li>
      </ul>
    </el-card>
    
    <el-card class="progress-card" v-if="importing">
      <template #header>
        <span>导入进度</span>
      </template>
      <el-steps :active="currentStep" finish-status="success">
        <el-step title="创建项目" />
        <el-step title="解析文件" />
        <el-step title="导入章节" />
        <el-step title="完成" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { novelApi, contentApi } from '@/api'

const router = useRouter()
const formRef = ref(null)
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
  outline_path: ''
})

const rules = {
  title: [{ required: true, message: '请输入小说标题', trigger: 'blur' }],
  author: [{ required: true, message: '请输入作者名', trigger: 'blur' }],
  genre: [{ required: true, message: '请选择题材', trigger: 'change' }],
  target_word_count: [{ required: true, message: '请输入目标字数', trigger: 'blur' }]
}

const selectFile = () => {
  ElMessage.info('请直接输入文件路径，如：D:\\小说\\修仙从逃出生天开始.txt')
}

const selectOutline = () => {
  ElMessage.info('请直接输入文件路径，如：D:\\小说\\大纲.txt')
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
    const novel = await novelApi.create({
      title: form.title,
      author: form.author,
      genre: form.genre,
      target_word_count: form.target_word_count
    })
    createdNovelId.value = novel.id
    novelCreated.value = true
    
    currentStep.value = 2
    await contentApi.import({
      novel_id: novel.id,
      file_path: form.file_path
    })
    
    currentStep.value = 3
    ElMessage.success('导入成功！')
    
    setTimeout(() => {
      router.push(`/novel/${novel.id}`)
    }, 1000)
    
  } catch (error) {
    console.error('导入失败:', error)
    importing.value = false
    currentStep.value = 0
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
