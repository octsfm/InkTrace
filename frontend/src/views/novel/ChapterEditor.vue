<template>
  <div class="chapter-editor">
    <div class="page-header">
      <el-button @click="$router.push(`/novel/${route.params.id}`)">返回小说详情</el-button>
      <h2>{{ form.title || `第${form.number || ''}章` }}</h2>
      <el-button :loading="saving" @click="saveChapter('draft')">保存草稿</el-button>
      <el-button type="primary" :loading="saving" @click="saveChapter('chapter')">保存章节</el-button>
      <el-button @click="openImportDialog">导入章节</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <el-form label-width="80px">
            <el-form-item label="章节标题">
              <el-input v-model="form.title" />
            </el-form-item>
            <el-form-item label="正文内容">
              <el-input v-model="form.content" type="textarea" :rows="24" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="side-card">
          <template #header>
            <span>本章大纲</span>
          </template>
          <el-form label-position="top">
            <el-form-item label="目标">
              <el-input v-model="outline.goal" />
            </el-form-item>
            <el-form-item label="冲突">
              <el-input v-model="outline.conflict" />
            </el-form-item>
            <el-form-item label="关键事件（每行一个）">
              <el-input v-model="outline.eventsText" type="textarea" :rows="4" />
            </el-form-item>
            <el-form-item label="人物推进">
              <el-input v-model="outline.character_progress" />
            </el-form-item>
            <el-form-item label="结尾钩子">
              <el-input v-model="outline.ending_hook" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="outline.notes" type="textarea" :rows="3" />
            </el-form-item>
          </el-form>
          <el-button :loading="savingOutline" @click="saveOutline">保存大纲</el-button>
        </el-card>

        <el-card class="side-card">
          <template #header>
            <span>AI 工具</span>
          </template>
          <div class="ai-actions">
            <el-button @click="runAI('optimize')" :loading="aiLoading">优化</el-button>
            <el-button @click="runAI('continue')" :loading="aiLoading">续写</el-button>
            <el-button @click="runAI('rewrite')" :loading="aiLoading">风格改写</el-button>
            <el-button @click="runAI('analyze')" :loading="aiLoading">分析</el-button>
            <el-button type="primary" @click="runAI('generate')" :loading="aiLoading">按大纲生成</el-button>
          </div>
          <el-alert type="info" :closable="false" style="margin-top: 10px;" title="AI结果不会自动覆盖正文，请手动采纳。" />
        </el-card>
      </el-col>
    </el-row>

    <el-card class="result-card" v-if="aiResult || aiAnalysis">
      <template #header>
        <span>AI 结果</span>
      </template>
      <el-alert v-if="aiTip" :title="aiTip" type="warning" :closable="false" style="margin-bottom: 10px;" />
      <pre v-if="aiResult" class="result-text">{{ aiResult }}</pre>
      <el-descriptions v-if="aiAnalysis" :column="1" border>
        <el-descriptions-item label="字数">{{ aiAnalysis.word_count }}</el-descriptions-item>
        <el-descriptions-item label="段落数">{{ aiAnalysis.paragraph_count }}</el-descriptions-item>
        <el-descriptions-item label="关键事件">{{ (aiAnalysis.key_events || []).join('；') }}</el-descriptions-item>
      </el-descriptions>
      <div class="result-actions">
        <el-button type="success" @click="overwriteWithResult" :disabled="!aiResult">覆盖正文</el-button>
        <el-button @click="appendResultToContent" :disabled="!aiResult">插入正文末尾</el-button>
        <el-button type="info" @click="discardResult" :disabled="!aiResult && !aiAnalysis">放弃结果</el-button>
      </div>
    </el-card>

    <el-dialog v-model="importDialogVisible" title="导入章节" width="640px">
      <el-form label-width="90px">
        <el-form-item label="导入方式">
          <el-radio-group v-model="importMode">
            <el-radio value="paste">粘贴文本</el-radio>
            <el-radio value="upload">上传文件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="importMode === 'paste'" label="章节文本">
          <el-input v-model="importRawText" type="textarea" :rows="12" />
        </el-form-item>
        <el-form-item v-if="importMode === 'upload'" label="文本文件">
          <input ref="importFileInput" type="file" accept=".txt" @change="onImportFileSelected" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importingChapter" @click="confirmImportChapter">导入并分析</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { chapterEditorApi, novelApi, projectApi } from '@/api'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const savingOutline = ref(false)
const aiLoading = ref(false)
const importingChapter = ref(false)
const aiResult = ref('')
const aiAnalysis = ref(null)
const aiTip = ref('')
const importDialogVisible = ref(false)
const importMode = ref('paste')
const importRawText = ref('')
const importFileInput = ref(null)
const form = ref({
  id: '',
  number: 0,
  title: '',
  content: ''
})
const outline = ref({
  goal: '',
  conflict: '',
  eventsText: '',
  character_progress: '',
  ending_hook: '',
  notes: ''
})

const currentChapterId = ref('')
const chapterContext = ref({
  globalMemorySummary: '',
  globalOutlineSummary: '',
  recentChapterSummaries: [],
  memoryView: {}
})

const toOutlinePayload = () => ({
  goal: outline.value.goal,
  conflict: outline.value.conflict,
  events: outline.value.eventsText.split('\n').map((x) => x.trim()).filter(Boolean),
  character_progress: outline.value.character_progress,
  ending_hook: outline.value.ending_hook,
  notes: outline.value.notes
})

const fillOutline = (data) => {
  outline.value.goal = data?.goal || ''
  outline.value.conflict = data?.conflict || ''
  outline.value.eventsText = Array.isArray(data?.events) ? data.events.join('\n') : ''
  outline.value.character_progress = data?.character_progress || ''
  outline.value.ending_hook = data?.ending_hook || ''
  outline.value.notes = data?.notes || ''
}

const ensureChapterId = async () => {
  const chapterId = String(route.params.chapterId || '')
  if (chapterId && chapterId !== 'new') {
    currentChapterId.value = chapterId
    return chapterId
  }
  const created = await novelApi.createChapter(route.params.id, { title: '', content: '' })
  currentChapterId.value = created.id
  await router.replace(`/novel/${route.params.id}/chapters/${created.id}/edit${route.query.import ? '?import=1' : ''}`)
  return created.id
}

const loadChapter = async () => {
  const chapterId = await ensureChapterId()
  const data = await chapterEditorApi.get(chapterId)
  form.value = {
    id: data.id,
    number: data.number,
    title: data.title || '',
    content: data.content || ''
  }
  const outlineData = await chapterEditorApi.getOutline(chapterId)
  fillOutline(outlineData)
  const ctx = await chapterEditorApi.getContext(chapterId)
  chapterContext.value = {
    globalMemorySummary: ctx.global_memory_summary || '',
    globalOutlineSummary: ctx.global_outline_summary || '',
    recentChapterSummaries: ctx.recent_chapter_summaries || [],
    memoryView: ctx.memory_view || {}
  }
}

const saveChapter = async (saveType) => {
  try {
    saving.value = true
    await chapterEditorApi.save(currentChapterId.value, {
      chapter_id: currentChapterId.value,
      title: form.value.title,
      content: form.value.content
    })
    ElMessage.success(saveType === 'draft' ? '草稿已保存' : '章节已保存')
  } finally {
    saving.value = false
  }
}

const saveOutline = async () => {
  try {
    savingOutline.value = true
    await chapterEditorApi.saveOutline(currentChapterId.value, toOutlinePayload())
    ElMessage.success('大纲已保存')
  } finally {
    savingOutline.value = false
  }
}

const aiContextPayload = () => ({
  global_memory_summary: chapterContext.value.globalMemorySummary || '',
  global_outline_summary: chapterContext.value.globalOutlineSummary || '',
  recent_chapter_summaries: chapterContext.value.recentChapterSummaries || []
})

const runAI = async (action) => {
  try {
    aiLoading.value = true
    const payload = {
      content: form.value.content,
      style: '当前风格',
      target_word_count: 2200,
      outline: toOutlinePayload(),
      ...aiContextPayload()
    }
    let result
    if (action === 'optimize') result = await chapterEditorApi.optimize(currentChapterId.value, payload)
    else if (action === 'continue') result = await chapterEditorApi.continueWrite(currentChapterId.value, payload)
    else if (action === 'rewrite') result = await chapterEditorApi.rewriteStyle(currentChapterId.value, payload)
    else if (action === 'analyze') result = await chapterEditorApi.analyze(currentChapterId.value, payload)
    else result = await chapterEditorApi.generateFromOutline(currentChapterId.value, payload)
    aiResult.value = result.result_text || ''
    aiAnalysis.value = result.analysis || null
    const outlineDraft = result.outline_draft || result.analysis?.outline_draft
    if (outlineDraft) {
      fillOutline(outlineDraft)
      aiTip.value = action === 'analyze'
        ? 'AI 已更新本章大纲建议'
        : '已生成本章大纲草稿，请确认后保存'
    }
  } finally {
    aiLoading.value = false
  }
}

const overwriteWithResult = () => {
  if (!aiResult.value) return
  form.value.content = aiResult.value
  ElMessage.success('已覆盖正文，可继续编辑后保存')
}

const appendResultToContent = () => {
  if (!aiResult.value) return
  form.value.content = `${form.value.content || ''}\n\n${aiResult.value}`.trim()
  ElMessage.success('已插入正文末尾，可继续编辑后保存')
}

const discardResult = () => {
  aiResult.value = ''
  aiAnalysis.value = null
  aiTip.value = ''
  ElMessage.success('已放弃当前AI结果')
}

const openImportDialog = () => {
  importRawText.value = ''
  importDialogVisible.value = true
}

const onImportFileSelected = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  importRawText.value = await file.text()
}

const confirmImportChapter = async () => {
  if (!importRawText.value.trim()) {
    ElMessage.warning('请先输入或上传章节文本')
    return
  }
  try {
    importingChapter.value = true
    const result = await chapterEditorApi.importChapter(currentChapterId.value, {
      raw_text: importRawText.value,
      title: form.value.title,
      ...aiContextPayload()
    })
    form.value.title = result.title || form.value.title
    form.value.content = result.content || form.value.content
    fillOutline(result.outline_draft || {})
    aiResult.value = ''
    aiAnalysis.value = { outline_draft: result.outline_draft || {} }
    aiTip.value = '导入完成，系统已生成本章大纲草稿，请确认后保存'
    importDialogVisible.value = false
    ElMessage.success('章节已导入并生成大纲草稿')
  } finally {
    importingChapter.value = false
  }
}

onMounted(async () => {
  await loadChapter()
  if (String(route.query.import || '') === '1') {
    openImportDialog()
  }
  const byNovel = await projectApi.getByNovel(route.params.id)
  if (byNovel?.id && !chapterContext.value.globalMemorySummary) {
    const view = await projectApi.memoryViewV2(byNovel.id)
    chapterContext.value.globalMemorySummary = (view?.main_plot_lines || []).join('；')
    chapterContext.value.globalOutlineSummary = (view?.outline_summary || []).join('；')
  }
})
</script>

<style scoped>
.chapter-editor {
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.side-card {
  margin-bottom: 14px;
}

.ai-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.result-card {
  margin-top: 14px;
}

.result-text {
  white-space: pre-wrap;
  line-height: 1.7;
}

.result-actions {
  margin-top: 12px;
}
</style>
