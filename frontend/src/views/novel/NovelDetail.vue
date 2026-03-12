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
          续写小说
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
            <el-descriptions-item label="作者">{{ novel?.author }}</el-descriptions-item>
            <el-descriptions-item label="题材">{{ novel?.genre }}</el-descriptions-item>
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
              <span>分析工具</span>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="analyzeStyle">
                <el-icon class="tool-icon"><Reading /></el-icon>
                <div class="tool-name">文风分析</div>
                <div class="tool-desc">分析词汇、句式、修辞</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="tool-card" @click="analyzePlot">
                <el-icon class="tool-icon"><Connection /></el-icon>
                <div class="tool-name">剧情分析</div>
                <div class="tool-desc">人物、时间线、伏笔</div>
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
      <el-descriptions :column="1" border v-if="styleResult">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { novelApi, contentApi, exportApi } from '@/api'

const route = useRoute()
const novel = ref(null)
const chapters = ref([])
const loading = ref(true)
const styleDialogVisible = ref(false)
const plotDialogVisible = ref(false)
const styleResult = ref(null)
const plotResult = ref(null)

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

onMounted(() => {
  loadNovel()
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
</style>
