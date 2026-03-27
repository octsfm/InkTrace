<template>
  <div class="novel-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/novels')">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2 class="page-title">{{ novel?.title || '小说详情' }}</h2>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="$router.push(`/novel/${$route.params.id}/write`)">
          <el-icon><Edit /></el-icon>
          继续创作
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="info-card">
          <template #header>
            <span>基本信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="作者">{{ novel?.author || '未知' }}</el-descriptions-item>
            <el-descriptions-item label="题材">{{ formatGenre(novel?.genre) }}</el-descriptions-item>
            <el-descriptions-item label="当前字数">{{ formatNumber(novel?.current_word_count) }}</el-descriptions-item>
            <el-descriptions-item label="目标字数">{{ formatNumber(novel?.target_word_count) }}</el-descriptions-item>
            <el-descriptions-item label="章节数">{{ novel?.chapter_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ novel?.created_at?.substring(0, 10) }}</el-descriptions-item>
          </el-descriptions>

          <div class="progress-section">
            <span>完成进度</span>
            <el-progress
              :percentage="getProgress()"
              :stroke-width="12"
              style="margin-top: 10px;"
            />
          </div>
        </el-card>

        <el-card class="analysis-card">
          <template #header>
            <div class="card-header">
              <span>创作操作</span>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="triggerOrganize">
                <el-icon class="tool-icon"><Reading /></el-icon>
                <div class="tool-name">{{ organizeActionLabel }}</div>
                <div class="tool-desc">{{ organizeActionDesc }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="$router.push(`/novel/${$route.params.id}/write`)">
                <el-icon class="tool-icon"><Connection /></el-icon>
                <div class="tool-name">继续创作</div>
                <div class="tool-desc">基于最新章节继续生成后续剧情</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="exportNovel">
                <el-icon class="tool-icon"><Download /></el-icon>
                <div class="tool-name">导出小说</div>
                <div class="tool-desc">导出弹窗支持范围、格式和输出路径</div>
              </el-card>
            </el-col>
          </el-row>

          <div class="organize-actions">
            <el-button size="small" @click="startOrganize(true)" :loading="organizing">重新整理</el-button>
            <el-button size="small" type="warning" @click="stopOrganize" :disabled="!progressRunning">停止整理</el-button>
            <el-button size="small" type="primary" @click="resumeOrganize" :disabled="!progressResumable">继续整理</el-button>
          </div>
          <div v-if="organizing || organizeProgress.total > 0" class="organize-progress">
            <div class="organize-progress-text">{{ organizeProgress.message }}</div>
            <div class="organize-progress-meta">
              <span>进度：{{ organizeProgress.current || 0 }} / {{ organizeProgress.total || 0 }}</span>
              <span v-if="organizeProgress.current_chapter_title">当前章节：{{ organizeProgress.current_chapter_title }}</span>
            </div>
            <el-progress :percentage="organizeProgress.percent" :stroke-width="10" />
          </div>
        </el-card>

        <el-card class="memory-card">
          <template #header>
            <span>小说结构摘要</span>
          </template>
          <div v-if="memoryLoading" class="loading">
            <el-skeleton :rows="4" animated />
          </div>
          <el-collapse v-else v-model="memoryCollapse">
            <el-collapse-item title="大纲摘要" name="outline">
              <div v-if="outlineSummary.length === 0" class="empty-text">暂无数据</div>
              <ul v-else class="plot-list">
                <li v-for="(item, index) in outlineSummary" :key="`outline-${index}`">{{ item }}</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="人物（主角与关键配角）" name="characters">
              <div v-if="memoryCharacters.length === 0" class="empty-text">暂无数据</div>
              <div v-else class="memory-list">
                <div v-for="(item, index) in memoryCharacters" :key="item.name || index" class="memory-item">
                  <strong>{{ index === 0 ? '主角' : '配角' }}：{{ item.name || '未命名' }}</strong>
                  <span> - {{ item.brief || '暂无描述' }}</span>
                </div>
              </div>
            </el-collapse-item>
            <el-collapse-item title="世界观（背景设定）" name="world">
              <div v-if="!worldSettingSummary" class="empty-text">暂无数据</div>
              <div v-else class="summary-text">{{ worldSettingSummary }}</div>
            </el-collapse-item>
            <el-collapse-item title="剧情主线" name="plot">
              <div v-if="plotOutline.length === 0" class="empty-text">暂无数据</div>
              <ul v-else class="plot-list">
                <li v-for="(item, index) in plotOutline" :key="`plot-${index}`">{{ item }}</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="写作风格" name="style">
              <div v-if="styleTags.length === 0" class="empty-text">暂无数据</div>
              <div v-else class="style-tags">
                <el-tag v-for="(tag, index) in styleTags" :key="`style-${index}`" type="success">{{ tag }}</el-tag>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="chapters-card">
          <template #header>
            <div class="chapters-header">
              <span>章节列表</span>
              <div class="chapters-toolbar">
                <el-button type="primary" size="small" @click="createChapter">新建章节</el-button>
                <el-button size="small" @click="importChapterToNew">导入章节</el-button>
              </div>
            </div>
          </template>

          <div v-if="loading" class="loading">
            <el-skeleton :rows="5" animated />
          </div>

          <el-scrollbar v-else height="400px">
            <div
              v-for="chapter in chapters"
              :key="chapter.id"
              class="chapter-item"
            >
              <span class="chapter-title" @click="openChapterEditor(chapter)">第{{ chapter.number }}章 {{ chapter.title }}</span>
              <div class="chapter-actions">
                <span class="chapter-words">{{ chapter.word_count }}字</span>
                <el-button size="small" link @click.stop="openChapterEditor(chapter)">编辑</el-button>
                <el-button size="small" link @click.stop="importChapterToCurrent(chapter)">导入本章内容</el-button>
                <el-button type="danger" link size="small" @click.stop="deleteChapter(chapter)">
                  删除
                </el-button>
              </div>
            </div>

            <el-empty v-if="chapters.length === 0" description="暂无章节" />
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="styleDialogVisible" title="文风分析结果" width="600px">
      <el-descriptions v-if="styleResult" :column="1" border>
        <el-descriptions-item label="叙述视角">{{ styleResult.narrative_voice }}</el-descriptions-item>
        <el-descriptions-item label="对话风格">{{ styleResult.dialogue_style }}</el-descriptions-item>
        <el-descriptions-item label="节奏特征">{{ styleResult.pacing }}</el-descriptions-item>
        <el-descriptions-item label="修辞统计">
          <el-tag v-for="(count, key) in styleResult.rhetoric_stats" :key="key" style="margin-right: 5px;">
            {{ key }}: {{ count }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="plotDialogVisible" title="剧情分析结果" width="700px">
      <el-tabs v-if="plotResult">
        <el-tab-pane label="人物">
          <el-table :data="plotResult.characters" max-height="300">
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="appearance_count" label="出场次数" width="100" />
            <el-table-column prop="first_appearance_chapter" label="首次出场" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="时间线">
          <el-timeline>
            <el-timeline-item
              v-for="(event, index) in plotResult.timeline"
              :key="index"
              :timestamp="`第${event.chapter_number}章`"
            >
              {{ event.event_description }}
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>
        <el-tab-pane label="伏笔">
          <el-table :data="plotResult.foreshadowings" max-height="300">
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="chapter_number" label="章节" width="80" />
            <el-table-column prop="status" label="状态" width="80" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-dialog v-model="exportDialogVisible" title="导出小说" width="560px">
      <el-form label-width="100px">
        <el-form-item label="导出范围">
          <el-radio-group v-model="exportForm.scope">
            <el-radio value="full">全部导出</el-radio>
            <el-radio value="by_chapter">分章节导出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio value="markdown">Markdown (.md)</el-radio>
            <el-radio value="txt">TXT (.txt)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="exportForm.scope === 'full' ? '输出文件' : '输出目录'">
          <el-input v-model="exportForm.output_path" :placeholder="exportForm.scope === 'full' ? '例如：my_novel.md' : '例如：my_novel_chapters'" />
          <el-button
            style="margin-top: 8px;"
            :disabled="!window.electronAPI"
            @click="selectExportPath"
          >
            选择路径
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="submitExport">开始导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contentApi, exportApi, novelApi, projectApi } from '@/api'

const route = useRoute()
const router = useRouter()
const novel = ref(null)
const chapters = ref([])
const loading = ref(true)
const styleDialogVisible = ref(false)
const plotDialogVisible = ref(false)
const styleResult = ref(null)
const plotResult = ref(null)
const memoryData = ref({})
const projectId = ref('')
const memoryLoading = ref(false)
const memoryCollapse = ref(['outline', 'characters', 'world', 'plot', 'style'])
const organizing = ref(false)
const organizeProgress = ref({
  current: 0,
  total: 0,
  percent: 0,
  status: 'idle',
  stage: 'idle',
  message: '暂无整理任务',
  current_chapter_title: '',
  resumable: false
})
let organizePollTimer = null
const deletingChapter = ref(false)
const exportDialogVisible = ref(false)
const exporting = ref(false)
const exportForm = ref({
  scope: 'full',
  format: 'markdown',
  output_path: ''
})
const genreMap = {
  xuanhuan: '玄幻',
  xianxia: '仙侠',
  dushi: '都市',
  lishi: '历史',
  kehuan: '科幻',
  wuxia: '武侠',
  qihuan: '奇幻',
  other: '其他'
}

const asArray = (value) => (Array.isArray(value) ? value : (value ? [value] : []))
const isLowQualityText = (value) => {
  const text = String(value || '').trim()
  if (!text) return true
  if (text.includes('chunk=') || text.includes('分析完成')) return true
  if ((text.match(/\?/g) || []).length >= 3) return true
  return /(瑙|锛|€|缁|閸|绗|绔|妭)/.test(text)
}

const memoryCharacters = computed(() => {
  const source = asArray(memoryData.value?.characters)
  return source
    .slice(0, 8)
    .map((item) => ({
      name: String(item?.name || '').trim(),
      brief: asArray(item?.traits).slice(0, 3).join('、') || String(item?.role || '').trim() || '暂无描述'
    }))
    .filter((item) => !isLowQualityText(item.name) && !isLowQualityText(item.brief))
    .slice(0, 6)
})

const worldSettingSummary = computed(() => {
  const worldFacts = memoryData.value?.world_facts || {}
  const items = [
    ...asArray(worldFacts.background),
    ...asArray(worldFacts.power_system),
    ...asArray(worldFacts.organizations),
    ...asArray(worldFacts.locations),
    ...asArray(worldFacts.rules),
    ...asArray(worldFacts.artifacts)
  ]
  const text = items.map((item) => String(item)).filter((item) => !isLowQualityText(item)).join('；')
  return text ? text.slice(0, 320) : ''
})

const plotOutline = computed(() => {
  const viewLines = asArray(memoryData.value?.plot_outline).map((item) => String(item)).filter((item) => !isLowQualityText(item))
  if (viewLines.length) {
    return viewLines.slice(-8)
  }
  const chapterSummaries = asArray(memoryData.value?.chapter_summaries).map((item) => String(item)).filter((item) => !isLowQualityText(item))
  if (chapterSummaries.length) {
    return chapterSummaries.slice(-8)
  }
  const threads = asArray(memoryData.value?.plot_threads)
  return threads
    .map((item) => {
      if (typeof item === 'string') return item
      const title = item?.title || ''
      const points = asArray(item?.points)
      const tail = points.length ? points[points.length - 1] : ''
      return tail ? `${title}：${tail}` : title
    })
    .filter(Boolean)
    .slice(-8)
})

const styleTags = computed(() => {
  const styleProfile = memoryData.value?.style_profile || {}
  const tags = [
    ...asArray(styleProfile?.tone_tags),
    ...asArray(styleProfile?.rhythm_tags),
    styleProfile?.narrative_pov
  ].filter(Boolean)
  if (tags.length) {
    return tags.slice(0, 6)
  }
  const legacy = memoryData.value?.writing_style
  return typeof legacy === 'string' ? legacy.split('；').filter(Boolean).slice(0, 6) : []
})

const outlineSummary = computed(() => {
  const summary = memoryData.value?.outline_summary || memoryData.value?.outline_context?.summary || []
  return asArray(summary).map((item) => String(item)).filter((item) => !isLowQualityText(item)).slice(0, 6)
})

const organizeActionLabel = computed(() => {
  if (progressRunning.value) return '正在整理故事结构'
  if (progressResumable.value) return '继续整理故事结构'
  if (organizeProgress.value.status === 'done') return '再次整理故事结构'
  return '整理故事结构'
})

const organizeActionDesc = computed(() => {
  if (progressRunning.value) return '整理进行中，可在下方停止或等待完成'
  if (progressResumable.value) return '从上次中断的位置继续分析'
  if (organizeProgress.value.status === 'done') return '基于当前内容重新生成结构摘要'
  return '按当前内容整理人物、设定与主线'
})

const progressRunning = computed(() => organizeProgress.value.status === 'running')
const progressResumable = computed(() => !!organizeProgress.value.resumable && !progressRunning.value)
const lastOrganizeStatus = ref('')

const loadNovel = async () => {
  try {
    novel.value = await novelApi.get(route.params.id)
    chapters.value = novel.value.chapters || []
  } catch (error) {
    console.error('加载小说失败:', error)
  } finally {
    loading.value = false
  }
}

const loadMemory = async () => {
  memoryLoading.value = true
  try {
    if (!projectId.value) {
      const project = await projectApi.getByNovel(route.params.id)
      projectId.value = project?.id || ''
    }
    if (!projectId.value) {
      memoryData.value = {}
      return
    }
    const view = await projectApi.memoryViewV2(projectId.value)
    const raw = await projectApi.memoryV2(projectId.value)
    const memory = raw?.memory || {}
    const memoryView = view?.memory_view || {}
    memoryData.value = {
      ...memory,
      characters: memory?.characters || memoryView?.main_characters || [],
      world_facts: memory?.world_facts || { background: memoryView?.world_summary || [] },
      plot_outline: memoryView?.main_plot_lines || memory?.plot_outline || [],
      chapter_summaries: memory?.chapter_summaries || [],
      style_profile: memory?.style_profile || {},
      writing_style: memory?.writing_style || (memoryView?.style_tags || []).join('；'),
      current_progress: memoryView?.current_progress || memory?.current_progress || '',
      outline_summary: memoryView?.outline_summary || memory?.outline_context?.summary || []
    }
  } catch (error) {
    memoryData.value = {}
    console.error('加载 memory 失败:', error)
  } finally {
    memoryLoading.value = false
  }
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return `${(num / 10000).toFixed(1)}万`
  }
  return Number(num).toLocaleString()
}

const getProgress = () => {
  if (!novel.value?.target_word_count) return 0
  return Math.min(100, Math.round((novel.value.current_word_count / novel.value.target_word_count) * 100))
}

const formatGenre = (genre) => genreMap[genre] || genre || '未知'

const analyzeStyle = async () => {
  try {
    ElMessage.info('正在分析文风...')
    styleResult.value = await contentApi.analyzeStyle(route.params.id)
    styleDialogVisible.value = true
  } catch (error) {
    console.error('文风分析失败:', error)
  }
}

const analyzePlot = async () => {
  try {
    ElMessage.info('正在分析剧情...')
    plotResult.value = await contentApi.analyzePlot(route.params.id)
    plotDialogVisible.value = true
  } catch (error) {
    console.error('剧情分析失败:', error)
  }
}

const exportNovel = async () => {
  exportForm.value = {
    scope: 'full',
    format: 'markdown',
    output_path: `${novel.value?.title || 'novel'}.md`
  }
  exportDialogVisible.value = true
}

const selectExportPath = async () => {
  if (!window.electronAPI) return
  try {
    if (exportForm.value.scope === 'full') {
      const result = await window.electronAPI.selectFile({
        title: '选择导出文件',
        filters: exportForm.value.format === 'markdown'
          ? [{ name: 'Markdown', extensions: ['md'] }]
          : [{ name: 'Text', extensions: ['txt'] }]
      })
      if (!result.canceled && result.filePaths?.[0]) {
        exportForm.value.output_path = result.filePaths[0]
      }
      return
    }
    const result = await window.electronAPI.selectFolder({ title: '选择导出目录' })
    if (!result.canceled && result.filePaths?.[0]) {
      exportForm.value.output_path = result.filePaths[0]
    }
  } catch (error) {
    console.error('选择导出路径失败:', error)
  }
}

const submitExport = async () => {
  try {
    exporting.value = true
    const fallbackName = exportForm.value.scope === 'full'
      ? `${novel.value?.title || 'novel'}.${exportForm.value.format === 'markdown' ? 'md' : 'txt'}`
      : `${novel.value?.title || 'novel'}_chapters`
    const result = await exportApi.export({
      novel_id: route.params.id,
      scope: exportForm.value.scope,
      format: exportForm.value.format,
      output_path: exportForm.value.output_path || fallbackName
    })
    if (result.mode === 'file' && result.file_path) {
      const isAbsolutePath = /^[a-zA-Z]:[\\/]/.test(result.file_path) || result.file_path.startsWith('/')
      if (!isAbsolutePath) {
        const link = document.createElement('a')
        link.href = exportApi.download(result.file_path)
        link.target = '_blank'
        link.rel = 'noopener'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
      ElMessage.success(`导出成功：已生成 1 个文件，共 ${result.chapter_count} 章，${result.word_count} 字`)
    } else {
      ElMessage.success(`导出成功：已生成 ${result.file_count || result.chapter_count || 0} 个章节文件，输出目录 ${result.directory_path || ''}`)
    }
    exportDialogVisible.value = false
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    exporting.value = false
  }
}

const startOrganize = async (forceRebuild = false) => {
  try {
    organizing.value = true
    organizeProgress.value = {
      ...organizeProgress.value,
      status: 'running',
      message: forceRebuild ? '正在重新整理故事结构（0%）' : '正在整理故事结构（0%）',
      resumable: false
    }
    ElMessage.info(
      forceRebuild
        ? '正在从头重新整理故事结构...'
        : '正在整理故事结构...'
    )
    await contentApi.startOrganize(route.params.id, !!forceRebuild)
    await fetchOrganizeProgress()
    startOrganizeProgressPolling()
  } catch (error) {
    console.error('整理失败:', error)
  } finally {
    organizing.value = false
  }
}

const resumeOrganize = async () => {
  try {
    organizing.value = true
    await contentApi.resumeOrganize(route.params.id)
    await fetchOrganizeProgress()
    startOrganizeProgressPolling()
    ElMessage.success('已继续整理')
  } catch (error) {
    console.error('继续整理失败:', error)
  } finally {
    organizing.value = false
  }
}

const stopOrganize = async () => {
  try {
    await contentApi.stopOrganize(route.params.id)
    await fetchOrganizeProgress()
    stopOrganizeProgressPolling()
    ElMessage.success('已停止整理')
  } catch (error) {
    console.error('停止整理失败:', error)
  }
}

const triggerOrganize = () => {
  if (progressRunning.value) return
  if (progressResumable.value) {
    resumeOrganize()
    return
  }
  startOrganize(false)
}

const fetchOrganizeProgress = async () => {
  try {
    const progress = await contentApi.organizeProgress(route.params.id)
    const current = progress || organizeProgress.value
    organizeProgress.value = current
    if (current.status === 'done' && lastOrganizeStatus.value !== 'done') {
      await Promise.all([loadNovel(), loadMemory()])
      ElMessage.success('故事结构已更新')
    }
    lastOrganizeStatus.value = current.status || ''
  } catch (error) {
    console.error('加载整理进度失败:', error)
  }
}

const startOrganizeProgressPolling = () => {
  stopOrganizeProgressPolling()
  organizePollTimer = setInterval(async () => {
    await fetchOrganizeProgress()
    if (organizeProgress.value.status !== 'running') {
      stopOrganizeProgressPolling()
    }
  }, 1200)
}

const stopOrganizeProgressPolling = () => {
  if (organizePollTimer) {
    clearInterval(organizePollTimer)
    organizePollTimer = null
  }
}

const openChapterEditor = async (chapter) => {
  if (!chapter?.id) return
  router.push(`/novel/${route.params.id}/chapters/${chapter.id}/edit`)
}

const createChapter = async () => {
  router.push(`/novel/${route.params.id}/chapters/new`)
}

const importChapterToNew = () => {
  router.push(`/novel/${route.params.id}/chapters/new?import=1`)
}

const importChapterToCurrent = (chapter) => {
  if (!chapter?.id) return
  router.push(`/novel/${route.params.id}/chapters/${chapter.id}/edit?import=1`)
}

const deleteChapter = async (chapter) => {
  if (!chapter?.id) return
  try {
    await ElMessageBox.confirm(
      `确认删除“第${chapter.number || ''}章 ${chapter.title || ''}”？删除后无法恢复。`,
      '删除章节',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )
    deletingChapter.value = true
    await novelApi.deleteChapter(route.params.id, chapter.id)
    await loadNovel()
    ElMessage.success('章节已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除章节失败:', error)
    }
  } finally {
    deletingChapter.value = false
  }
}

onMounted(() => {
  loadNovel()
  loadMemory()
  fetchOrganizeProgress().then(() => {
    if (organizeProgress.value.status === 'running') {
      startOrganizeProgressPolling()
    }
  })
})

onBeforeUnmount(() => {
  stopOrganizeProgressPolling()
})
</script>

<style scoped>
.novel-detail {
  padding: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.info-card,
.analysis-card,
.memory-card,
.chapters-card {
  margin-bottom: 20px;
}

.progress-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.tool-card {
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
}

.tool-card:hover {
  transform: translateY(-4px);
}

.tool-icon {
  font-size: 36px;
  color: #409eff;
  margin-bottom: 10px;
}

.tool-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 5px;
}

.tool-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.organize-progress {
  margin-top: 14px;
  padding: 12px;
  background: #f8fbff;
  border: 1px solid #e6f0ff;
  border-radius: 8px;
}

.organize-actions {
  margin-top: 14px;
}

.organize-progress-text {
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
}

.organize-progress-meta {
  margin-bottom: 8px;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #909399;
  font-size: 12px;
}

.chapter-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
}

.chapters-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chapters-toolbar {
  display: flex;
  gap: 8px;
}

.chapter-item:hover {
  background-color: #f5f7fa;
}

.chapter-title {
  color: #303133;
}

.chapter-words {
  color: #909399;
  font-size: 12px;
}

.chapter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading {
  padding: 20px;
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-item {
  line-height: 1.6;
}

.summary-text {
  line-height: 1.8;
}

.plot-list {
  margin: 0;
  padding-left: 18px;
  line-height: 1.8;
}

.style-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-text {
  color: #909399;
}
</style>
