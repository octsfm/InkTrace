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
            <el-descriptions-item label="章节数">{{ novel?.chapter_count }}</el-descriptions-item>
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
              <el-card shadow="hover" class="tool-card" @click="organizeStory()">
                <el-icon class="tool-icon"><Reading /></el-icon>
                <div class="tool-name">{{ organizeActionLabel }}</div>
                <div class="tool-desc">{{ organizeActionDesc }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="$router.push(`/novel/${$route.params.id}/write`)">
                <el-icon class="tool-icon"><Connection /></el-icon>
                <div class="tool-name">继续创作</div>
                <div class="tool-desc">基于既有设定延展下一章</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="exportNovel">
                <el-icon class="tool-icon"><Download /></el-icon>
                <div class="tool-name">导出小说</div>
                <div class="tool-desc">导出Markdown格式</div>
              </el-card>
            </el-col>
          </el-row>
          <div class="organize-actions">
            <el-button size="small" @click="organizeStory(true)" :loading="organizing">重新整理</el-button>
          </div>
          <div v-if="organizing || organizeProgress.total > 0" class="organize-progress">
            <div class="organize-progress-text">{{ organizeProgress.message }}</div>
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
                <li v-for="(item, index) in plotOutline" :key="index">{{ item }}</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="写作风格" name="style">
              <div v-if="styleTags.length === 0" class="empty-text">暂无数据</div>
              <div v-else class="style-tags">
                <el-tag v-for="(tag, index) in styleTags" :key="index" type="success">{{ tag }}</el-tag>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="chapters-card">
          <template #header>
            <span>章节列表</span>
          </template>

          <div v-if="loading" class="loading">
            <el-skeleton :rows="5" animated />
          </div>

          <el-scrollbar v-else height="400px">
            <div
              v-for="chapter in chapters"
              :key="chapter.id"
              class="chapter-item"
              @click="openChapterEditor(chapter)"
            >
              <span class="chapter-title">第{{ chapter.number }}章 {{ chapter.title }}</span>
              <span class="chapter-words">{{ chapter.word_count }}字</span>
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
        <el-descriptions-item label="节奏特点">{{ styleResult.pacing }}</el-descriptions-item>
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
              :timestamp="'第' + event.chapter_number + '章'"
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

    <el-dialog v-model="chapterDialogVisible" title="章节编辑" width="800px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editingChapter.title" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editingChapter.content" type="textarea" :rows="14" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingChapter" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contentApi, exportApi, novelApi } from '@/api'

const route = useRoute()
const novel = ref(null)
const chapters = ref([])
const loading = ref(true)
const styleDialogVisible = ref(false)
const plotDialogVisible = ref(false)
const styleResult = ref(null)
const plotResult = ref(null)
const memoryData = ref({})
const memoryLoading = ref(false)
const memoryCollapse = ref(['characters', 'world', 'plot', 'style'])
const organizing = ref(false)
const organizeProgress = ref({
  current: 0,
  total: 0,
  percent: 0,
  status: 'idle',
  message: '暂无整理任务'
})
let organizePollTimer = null
const chapterDialogVisible = ref(false)
const savingChapter = ref(false)
const editingChapter = ref({
  id: '',
  number: 0,
  title: '',
  content: ''
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

const memoryCharacters = computed(() => {
  const source = memoryData.value?.characters || []
  return source.slice(0, 5).map((item) => {
    const traits = (item?.traits || []).slice(0, 3).join('、')
    return {
      name: item?.name || '',
      brief: traits || '暂无性格标签'
    }
  })
})

const worldSettingSummary = computed(() => {
  const source = memoryData.value?.world_settings || []
  const items = Array.isArray(source) ? source : [source]
  const text = items.map((item) => String(item)).join('；')
  return text ? text.slice(0, 200) : ''
})

const plotOutline = computed(() => {
  const explicitOutline = memoryData.value?.plot_outline || []
  const outlineItems = Array.isArray(explicitOutline) ? explicitOutline : [explicitOutline].filter(Boolean)
  if (outlineItems.length > 0) {
    return outlineItems.map((item) => String(item)).slice(0, 8)
  }
  const threads = memoryData.value?.plot_threads || []
  return threads
    .map((item) => {
      if (typeof item === 'string') return item
      const title = item?.title || ''
      const points = item?.points || []
      const tail = points.length ? points[points.length - 1] : ''
      return tail ? `${title}：${tail}` : title
    })
    .filter(Boolean)
    .slice(0, 8)
})

const styleTags = computed(() => {
  const style = memoryData.value?.writing_style || memoryData.value?.style_profile || {}
  if (typeof style === 'string') {
    return style ? [style] : []
  }
  return [style.tone, style.pacing, style.narrative_style].filter((item) => !!item)
})

const organizeActionLabel = computed(() => {
  if (organizeProgress.value.resumable) return '继续整理故事结构'
  if (organizeProgress.value.status === 'done') return '再次整理故事结构'
  return '整理故事结构'
})

const organizeActionDesc = computed(() => {
  if (organizeProgress.value.resumable) return '从上次中断的位置继续分析'
  if (organizeProgress.value.status === 'done') return '基于当前内容重新生成结构摘要'
  return '按当前内容整理人物、设定与主线'
})

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
    const res = await contentApi.memory(route.params.id)
    memoryData.value = res?.memory || {}
  } catch (error) {
    memoryData.value = {}
    console.error('加载memory失败:', error)
  } finally {
    memoryLoading.value = false
  }
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
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
  try {
    const result = await exportApi.export({
      novel_id: route.params.id,
      output_path: `exports/${novel.value.title}.md`,
      format: 'markdown'
    })
    ElMessage.success(`导出成功！共 ${result.chapter_count} 章，${result.word_count} 字`)
  } catch (error) {
    console.error('导出失败:', error)
  }
}

const organizeStory = async (forceRebuild = false) => {
  try {
    organizing.value = true
    if (forceRebuild || !organizeProgress.value.resumable) {
      organizeProgress.value = {
        current: 0,
        total: 0,
        percent: 0,
        status: 'running',
        message: forceRebuild ? '正在重新整理故事结构（0%）' : '正在初始化整理任务（0%）',
        resumable: false
      }
    }
    startOrganizeProgressPolling()
    ElMessage.info(
      forceRebuild
        ? '正在从头重新整理故事结构...'
        : (organizeProgress.value.resumable ? '正在继续整理故事结构...' : '正在整理故事结构...')
    )
    await contentApi.organize(route.params.id, forceRebuild)
    await fetchOrganizeProgress()
    await loadMemory()
    ElMessage.success('故事结构已更新')
  } catch (error) {
    console.error('整理失败:', error)
  } finally {
    organizing.value = false
    stopOrganizeProgressPolling()
  }
}

const fetchOrganizeProgress = async () => {
  try {
    const progress = await contentApi.organizeProgress(route.params.id)
    organizeProgress.value = progress || organizeProgress.value
  } catch (error) {
    console.error('加载整理进度失败:', error)
  }
}

const startOrganizeProgressPolling = () => {
  stopOrganizeProgressPolling()
  organizePollTimer = setInterval(async () => {
    await fetchOrganizeProgress()
    if (organizeProgress.value.status === 'done' || organizeProgress.value.status === 'error') {
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
  try {
    const detail = await novelApi.getChapter(route.params.id, chapter.id)
    editingChapter.value = {
      id: detail.id,
      number: detail.number,
      title: detail.title || '',
      content: detail.content || ''
    }
    chapterDialogVisible.value = true
  } catch (error) {
    console.error('加载章节详情失败:', error)
  }
}

const saveChapter = async () => {
  if (!editingChapter.value.id) return
  try {
    savingChapter.value = true
    await novelApi.updateChapter(route.params.id, editingChapter.value.id, {
      title: editingChapter.value.title,
      content: editingChapter.value.content
    })
    chapterDialogVisible.value = false
    await loadNovel()
    ElMessage.success('章节已保存')
  } catch (error) {
    console.error('保存章节失败:', error)
  } finally {
    savingChapter.value = false
  }
}

onMounted(() => {
  loadNovel()
  loadMemory()
  fetchOrganizeProgress()
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

.chapter-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
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
