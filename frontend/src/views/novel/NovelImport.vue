<template>
  <div class="novel-import">
    <div class="page-header">
      <h2 class="page-title">导入小说</h2>
    </div>

    <el-card class="import-card">
      <el-alert
        title="单章导入请在作品详情页或章节编辑页执行，这里用于新建作品或整本导入。"
        type="info"
        :closable="false"
        style="margin-bottom: 12px;"
      />

      <el-form ref="formRef" :model="form" label-width="100px" :rules="rules">
        <el-form-item label="导入模式">
          <el-radio-group v-model="form.import_mode">
            <el-radio value="empty">创建空白作品</el-radio>
            <el-radio value="full">整本导入</el-radio>
          </el-radio-group>
        </el-form-item>

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
          <el-input-number
            v-model="form.target_word_count"
            :min="10000"
            :max="50000000"
            :step="10000"
          />
        </el-form-item>

        <el-form-item label="简介">
          <el-input
            v-model="form.intro"
            type="textarea"
            :rows="3"
            placeholder="可选，输入小说简介"
          />
        </el-form-item>

        <el-form-item label="标签">
          <el-input v-model="form.tagsText" placeholder="可选，多个标签请用逗号分隔" />
        </el-form-item>

        <el-form-item label="整理批次">
          <el-select v-model="form.batch_size_chapters" style="width: 100%">
            <el-option :value="null" label="自动（推荐）" />
            <el-option :value="3" label="每批 3 章" />
            <el-option :value="5" label="每批 5 章" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.import_mode !== 'empty'" label="小说文件" prop="file_path">
          <el-input v-model="form.file_path" placeholder="请输入小说文件路径">
            <template #append>
              <el-button @click="selectFile">选择文件</el-button>
            </template>
          </el-input>
          <input
            ref="fileInput"
            type="file"
            style="display: none"
            accept=".txt"
            @change="handleFileSelect"
          />
          <div class="file-tip">支持 `.txt` 格式，系统会尝试自动识别章节结构。</div>
        </el-form-item>

        <el-form-item label="大纲文件">
          <el-input v-model="form.outline_path" placeholder="可选，输入大纲文件路径">
            <template #append>
              <el-button @click="selectOutline">选择文件</el-button>
            </template>
          </el-input>
          <input
            ref="outlineInput"
            type="file"
            style="display: none"
            accept=".txt"
            @change="handleOutlineSelect"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="importing" @click="handleImport">
            开始导入
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="importing || createdNovelId" class="progress-card">
      <template #header>
        <span>导入与整理进度</span>
      </template>

      <el-steps :active="currentStep" finish-status="success">
        <el-step title="创建项目" />
        <el-step title="解析文件" />
        <el-step title="整理结构" />
        <el-step title="完成" />
      </el-steps>

      <div v-if="organizeProgress.total > 0" class="organize-progress">
        <div class="organize-progress-text">{{ organizeProgress.message }}</div>
        <div class="organize-progress-meta">
          <span>状态：{{ formatOrganizeStatus(organizeProgress.status) }}</span>
          <span>阶段：{{ organizeProgress.stage || '暂无' }}</span>
          <span>策略：{{ organizeProgress.strategy || 'chapter_first' }}</span>
          <span>进度：{{ organizeProgress.current || 0 }} / {{ organizeProgress.total || 0 }}</span>
          <span>百分比：{{ organizeProgress.percent || 0 }}%</span>
          <span v-if="organizeProgress.effective_batch_size > 0">
            实际批次：{{ organizeProgress.effective_batch_size }}
          </span>
          <span v-if="organizeProgress.batch_total > 0">
            当前批次：{{ organizeProgress.batch_no || 0 }} / {{ organizeProgress.batch_total || 0 }}
          </span>
          <span v-if="organizeProgress.chunked_chapter_count > 0">
            分块章节：{{ organizeProgress.chunked_chapter_count }}
          </span>
          <span v-if="organizeProgress.current_chapter_title">
            当前章节：{{ organizeProgress.current_chapter_title }}
          </span>
        </div>
        <el-progress :percentage="organizeProgress.percent" :stroke-width="10" />

        <el-alert
          v-if="terminalOrganizeStatuses.includes(organizeProgress.status) && organizeTerminalMessage"
          class="status-alert"
          :type="organizeTerminalAlertType"
          :closable="false"
          :title="organizeTerminalMessage"
        />

        <div class="progress-actions">
          <el-button
            size="small"
            :disabled="!['running', 'resume_requested'].includes(organizeProgress.status)"
            @click="pauseOrganize"
          >
            暂停整理
          </el-button>
          <el-button
            size="small"
            :disabled="!['paused', 'pause_requested'].includes(organizeProgress.status)"
            @click="resumeOrganize"
          >
            继续整理
          </el-button>
          <el-button
            size="small"
            :disabled="!['running', 'paused', 'pause_requested', 'resume_requested'].includes(organizeProgress.status)"
            @click="cancelOrganize"
          >
            取消整理
          </el-button>
          <el-button
            size="small"
            :disabled="!['done', 'error', 'cancelled', 'paused'].includes(organizeProgress.status)"
            @click="retryOrganize"
          >
            重试整理
          </el-button>
          <el-button size="small" @click="goToDetail">查看作品详情</el-button>
        </div>
      </div>
    </el-card>

    <el-card v-if="chapterPreview.length > 0" class="import-card">
      <template #header>
        <span>导入预览（共 {{ chapterPreview.length }} 章）</span>
      </template>
      <el-table :data="chapterPreview" size="small">
        <el-table-column prop="number" label="章号" width="90" />
        <el-table-column prop="title" label="章节标题" min-width="220" />
        <el-table-column prop="word_count" label="字数" width="100" />
      </el-table>
    </el-card>

    <el-card v-if="!novelCreated" class="tip-card">
      <template #header>
        <span>导入说明</span>
      </template>
      <ul class="tip-list">
        <li>支持 TXT 格式的小说文件。</li>
        <li>系统会尝试自动识别“第一章”“第 1 章”“Chapter 1”等章节标题。</li>
        <li>大纲文件可包含人物设定、背景说明和故事规划。</li>
        <li>导入完成后会进入整理流程，随后可以进入写作工作台继续创作。</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { contentApi, novelApi, projectApi } from '@/api'
import { formatOrganizeStatus } from '@/constants/display'

const router = useRouter()
const formRef = ref(null)
const fileInput = ref(null)
const outlineInput = ref(null)
const importing = ref(false)
const novelCreated = ref(false)
const createdNovelId = ref('')
const currentStep = ref(0)
const chapterPreview = ref([])
const lastOrganizeNoticeKey = ref('')

let organizePollTimer = null
let organizePollController = null
let organizePollSeq = 0

const activeOrganizeStatuses = ['running', 'pause_requested', 'resume_requested', 'cancelling']
const terminalOrganizeStatuses = ['paused', 'cancelled', 'error', 'done']

const organizeProgress = ref({
  status: 'idle',
  stage: '',
  current: 0,
  total: 0,
  percent: 0,
  strategy: 'chapter_first',
  effective_batch_size: 0,
  batch_no: 0,
  batch_total: 0,
  chunked_chapter_count: 0,
  current_chapter_title: '',
  task_id: '',
  message: '尚未开始整理',
  last_error: ''
})

const organizeTerminalAlertType = computed(() => {
  if (organizeProgress.value.status === 'error') return 'error'
  if (organizeProgress.value.status === 'done') return 'success'
  return 'warning'
})

const organizeTerminalMessage = computed(() => (
  organizeProgress.value.last_error || organizeProgress.value.message || ''
))

const form = reactive({
  import_mode: 'full',
  title: '',
  author: '',
  genre: 'xianxia',
  target_word_count: 100000,
  intro: '',
  tagsText: '',
  batch_size_chapters: null,
  file_path: '',
  outline_path: '',
  selectedFile: null,
  selectedOutline: null
})

const validateFilePath = (_rule, value, callback) => {
  if (form.import_mode === 'empty') {
    callback()
    return
  }
  if (!String(value || '').trim() && !form.selectedFile) {
    callback(new Error('请输入小说文件路径'))
    return
  }
  callback()
}

const rules = {
  title: [{ required: true, message: '请输入小说标题', trigger: 'blur' }],
  author: [{ required: true, message: '请输入作者名', trigger: 'blur' }],
  genre: [{ required: true, message: '请选择题材', trigger: 'change' }],
  target_word_count: [{ required: true, message: '请输入目标字数', trigger: 'blur' }],
  file_path: [{ validator: validateFilePath, trigger: 'blur' }]
}

const notifyOrganizeTerminalStatus = () => {
  const status = String(organizeProgress.value.status || '')
  const message = organizeTerminalMessage.value
  if (!terminalOrganizeStatuses.includes(status) || !message) return
  const noticeKey = `${organizeProgress.value?.task_id || ''}:${status}:${message}`
  if (lastOrganizeNoticeKey.value === noticeKey) return
  lastOrganizeNoticeKey.value = noticeKey

  if (status === 'done') {
    ElMessage.success(message)
    return
  }
  if (status === 'error') {
    ElMessage.error(message)
    return
  }
  ElMessage.warning(message)
}

const selectFile = async () => {
  if (window.electronAPI?.selectFile) {
    const result = await window.electronAPI.selectFile({
      title: '选择小说文件',
      filters: [
        { name: '文本文件', extensions: ['txt'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    })
    if (result?.filePath) {
      form.file_path = result.filePath
      await previewChapters()
    }
    return
  }
  fileInput.value?.click()
}

const selectOutline = async () => {
  if (window.electronAPI?.selectFile) {
    const result = await window.electronAPI.selectFile({
      title: '选择大纲文件',
      filters: [
        { name: '文本文件', extensions: ['txt'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    })
    if (result?.filePath) {
      form.outline_path = result.filePath
    }
    return
  }
  outlineInput.value?.click()
}

const handleFileSelect = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  form.file_path = file.name
  form.selectedFile = file
  await previewChapters()
}

const handleOutlineSelect = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  form.outline_path = file.name
  form.selectedOutline = file
}

const parseChapterPreviewFromText = (text) => {
  const normalized = String(text || '')
  const blocks = normalized
    .split(/\n(?=(第[\d一二三四五六七八九十百千万零两]+章|Chapter\s+\d+))/i)
    .map((item) => item.trim())
    .filter(Boolean)

  return blocks.slice(0, 50).map((item, index) => {
    const lines = item.split('\n').map((line) => line.trim()).filter(Boolean)
    const firstLine = lines[0] || ''
    const content = lines.slice(1).join('\n')
    const wordCount = content ? content.replace(/\s+/g, '').length : firstLine.length
    return {
      number: index + 1,
      title: firstLine || `第 ${index + 1} 章`,
      word_count: wordCount
    }
  })
}

const previewChapters = async () => {
  if (form.import_mode === 'empty') {
    chapterPreview.value = []
    return
  }
  try {
    if (!window.electronAPI && form.selectedFile) {
      const text = await form.selectedFile.text()
      chapterPreview.value = parseChapterPreviewFromText(text)
      return
    }
    if (!form.file_path) return
    const result = await projectApi.importPreview({ file_path: form.file_path })
    chapterPreview.value = Array.isArray(result?.chapters) ? result.chapters : []
  } catch (error) {
    console.error('预览章节失败:', error)
  }
}

const stopOrganizePolling = () => {
  if (organizePollTimer) {
    clearInterval(organizePollTimer)
    organizePollTimer = null
  }
  if (organizePollController) {
    organizePollController.abort()
    organizePollController = null
  }
}

const fetchOrganizeProgress = async () => {
  if (!createdNovelId.value) return
  const currentSeq = ++organizePollSeq
  if (organizePollController) {
    organizePollController.abort()
  }
  organizePollController = new AbortController()

  try {
    const progress = await contentApi.organizeProgress(createdNovelId.value, {
      signal: organizePollController.signal
    })
    if (currentSeq !== organizePollSeq) return

    organizeProgress.value = progress || organizeProgress.value

    if (organizeProgress.value.status === 'done') {
      currentStep.value = 3
      importing.value = false
      stopOrganizePolling()
      notifyOrganizeTerminalStatus()
      return
    }

    if (activeOrganizeStatuses.includes(organizeProgress.value.status)) {
      lastOrganizeNoticeKey.value = ''
      currentStep.value = 2
      return
    }

    if (terminalOrganizeStatuses.includes(organizeProgress.value.status)) {
      currentStep.value = 2
      importing.value = false
      stopOrganizePolling()
      notifyOrganizeTerminalStatus()
    }
  } catch (error) {
    if (error?.code === 'ERR_CANCELED' || String(error?.message || '').toLowerCase().includes('canceled')) {
      return
    }
    console.error('读取整理进度失败:', error)
  } finally {
    if (organizePollController?.signal?.aborted !== true) {
      organizePollController = null
    }
  }
}

const startOrganizePolling = () => {
  stopOrganizePolling()
  organizePollTimer = setInterval(async () => {
    await fetchOrganizeProgress()
    if (!activeOrganizeStatuses.includes(organizeProgress.value.status)) {
      stopOrganizePolling()
    }
  }, 3000)
}

const startOrganize = async (forceRebuild = false) => {
  if (!createdNovelId.value) return
  await contentApi.startOrganize(
    createdNovelId.value,
    forceRebuild,
    'full_reanalyze',
    form.batch_size_chapters
  )
  await fetchOrganizeProgress()
  startOrganizePolling()
}

const pauseOrganize = async () => {
  if (!createdNovelId.value) return
  await contentApi.pauseOrganize(createdNovelId.value)
  await fetchOrganizeProgress()
  startOrganizePolling()
}

const resumeOrganize = async () => {
  if (!createdNovelId.value) return
  await contentApi.resumeOrganize(createdNovelId.value, '', form.batch_size_chapters)
  await fetchOrganizeProgress()
  startOrganizePolling()
  ElMessage.success('已继续整理')
}

const cancelOrganize = async () => {
  if (!createdNovelId.value) return
  await contentApi.cancelOrganize(createdNovelId.value)
  await fetchOrganizeProgress()
  startOrganizePolling()
}

const retryOrganize = async () => {
  if (!createdNovelId.value) return
  await contentApi.retryOrganize(createdNovelId.value, 'full_reanalyze', form.batch_size_chapters)
  await fetchOrganizeProgress()
  startOrganizePolling()
}

const createTags = () => (
  String(form.tagsText || '')
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean)
)

const handleImport = async () => {
  try {
    await formRef.value?.validate?.()
  } catch {
    return
  }

  if (form.import_mode !== 'empty' && !form.file_path && !form.selectedFile) {
    ElMessage.warning('请输入小说文件路径')
    return
  }

  importing.value = true
  currentStep.value = 1

  try {
    let novel = null

    if (form.import_mode === 'empty') {
      const created = await novelApi.create({
        title: form.title,
        author: form.author,
        genre: form.genre,
        summary: form.intro || '',
        target_word_count: form.target_word_count,
        tags: createTags()
      })
      novel = created?.novel || created
      createdNovelId.value = String(novel?.id || created?.id || '')
      novelCreated.value = true
      currentStep.value = 3
      ElMessage.success('空白作品创建成功')
      return
    }

    currentStep.value = 2
    ElMessage.info('正在整理故事结构...')

    if (!window.electronAPI && form.selectedFile) {
      const formData = new FormData()
      formData.append('file', form.selectedFile)
      formData.append('project_name', form.title)
      formData.append('author', form.author || '')
      formData.append('genre', form.genre)
      formData.append('import_mode', form.import_mode)
      formData.append('summary', form.intro || '')
      formData.append('target_word_count', String(form.target_word_count || ''))
      formData.append('tags', JSON.stringify(createTags()))
      formData.append('outline_path', form.outline_path || '')
      formData.append('auto_organize', 'false')
      const result = await projectApi.importV2Upload(formData)
      novel = result?.novel || result?.project || result
    } else {
      const result = await projectApi.importV2({
        project_name: form.title,
        title: form.title,
        author: form.author || '',
        genre: form.genre,
        summary: form.intro || '',
        target_word_count: form.target_word_count,
        tags: createTags(),
        file_path: form.file_path,
        outline_path: form.outline_path || '',
        import_mode: form.import_mode,
        auto_organize: false
      })
      novel = result?.novel || result?.project || result
    }

    createdNovelId.value = String(novel?.id || novel?.novel_id || novel?.project_id || '')
    novelCreated.value = true

    if (createdNovelId.value) {
      await startOrganize(true)
    }

    currentStep.value = 3
    ElMessage.success('导入完成，已开始整理结构')
    sessionStorage.setItem(
      'inktrace_continue_hint',
      JSON.stringify({
        novelId: createdNovelId.value,
        message: '已完成分析，是否继续创作下一章？',
        defaultGoal: '下一章：承接上一章推进主线。'
      })
    )
  } catch (error) {
    console.error('导入失败:', error)
  } finally {
    importing.value = false
  }
}

const goToDetail = () => {
  if (!createdNovelId.value) return
  router.push(`/works/${createdNovelId.value}`)
}

onBeforeUnmount(() => {
  stopOrganizePolling()
})
</script>

<style scoped>
.novel-import {
  --import-bg: var(--ink-bg-app);
  --import-surface: var(--ink-surface-1);
  --import-surface-soft: var(--ink-surface-2);
  --import-border: var(--ink-border);
  --import-border-strong: var(--ink-border-strong);
  --import-title: var(--ink-text-primary);
  --import-text: var(--ink-text-secondary);
  --import-muted: var(--ink-text-muted);

  padding: 20px;
  color: var(--import-text);
}

.page-title {
  color: var(--import-title);
}

.import-card,
.progress-card,
.tip-card {
  max-width: 800px;
  margin-bottom: 20px;
  border-radius: 20px;
}

.file-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--import-muted);
}

.tip-list {
  padding-left: 20px;
  color: var(--import-text);
  line-height: 1.9;
}

.organize-progress {
  margin-top: 16px;
}

.organize-progress-text {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--import-text);
}

.organize-progress-meta {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--import-muted);
}

.progress-actions {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-alert {
  margin-top: 12px;
}
</style>
