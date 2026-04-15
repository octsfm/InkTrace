<template>
  <div class="novel-list">
    <section class="dashboard-hero">
      <div class="hero-main">
        <div class="hero-eyebrow">工作台</div>
        <h1 class="hero-title">进入你的小说工作区</h1>
        <p class="hero-description">
          这里现在只负责一件事：帮你快速找到要继续写的小说，并直接进入对应工作区。
        </p>
        <div class="hero-actions">
          <el-button v-if="featuredNovel" type="primary" @click="openWorkspace(featuredNovel.id)">
            <el-icon><Edit /></el-icon>
            继续最近工作台
          </el-button>
          <el-button v-else type="primary" @click="$router.push('/import')">
            <el-icon><Plus /></el-icon>
            导入小说
          </el-button>
          <el-button v-if="featuredNovel" plain @click="openWorkspace(featuredNovel.id, { section: 'overview' })">
            打开概览
          </el-button>
          <el-button v-else plain @click="$router.push('/config')">模型配置</el-button>
        </div>
      </div>

      <div class="hero-side">
        <div v-if="featuredNovel" class="hero-featured-card">
          <div class="featured-label">最近工作区</div>
          <div class="featured-title">{{ featuredNovel.title }}</div>
          <div class="featured-meta">
            最近更新 {{ formatDate(featuredNovel.updated_at) }} · 第 {{ featuredNovel.chapter_count || 0 }} 章
          </div>
          <div class="risk-badge-row">
            <span class="risk-badge" :class="getTaskRiskTone(featuredNovel.id).className">{{ getTaskRiskTone(featuredNovel.id).label }}</span>
          </div>
          <div class="featured-risk" :class="{ warning: hasTaskRisk(featuredNovel.id) }">
            {{ getTaskRiskText(featuredNovel.id) }}
          </div>
          <div class="featured-actions">
            <button type="button" class="featured-action primary" @click="openWorkspace(featuredNovel.id)">
              继续写作
            </button>
            <button
              v-if="getTaskSummary(featuredNovel.id).failed > 0"
              type="button"
              class="featured-action warning"
              @click="openWorkspace(featuredNovel.id, { section: 'tasks' })"
            >
              处理失败任务
            </button>
            <button type="button" class="featured-action" @click="openWorkspace(featuredNovel.id, { section: 'overview' })">
              概览
            </button>
            <button type="button" class="featured-action" @click="openWorkspace(featuredNovel.id, { section: 'structure' })">
              结构
            </button>
            <button type="button" class="featured-action" @click="openWorkspace(featuredNovel.id, { section: 'chapters' })">
              章节
            </button>
            <button type="button" class="featured-action" @click="openWorkspace(featuredNovel.id, { section: 'tasks' })">
              任务
            </button>
          </div>
        </div>
        <div class="hero-stat">
          <span class="hero-stat-label">小说总数</span>
          <span class="hero-stat-value">{{ novels.length }}</span>
        </div>
        <div class="hero-stat">
          <span class="hero-stat-label">创作中</span>
          <span class="hero-stat-value">{{ activeNovelCount }}</span>
        </div>
        <div class="hero-stat">
          <span class="hero-stat-label">总章节</span>
          <span class="hero-stat-value">{{ totalChapterCount }}</span>
        </div>
      </div>
    </section>

    <section v-if="recentNovels.length" class="dashboard-section recent-section">
      <div class="section-heading">
        <div>
          <h2>最近继续创作</h2>
          <p>从最近更新的小说直接回到工作区。</p>
        </div>
      </div>

      <div class="recent-grid">
        <button
          v-for="novel in recentNovels"
          :key="novel.id"
          type="button"
          class="recent-card"
          @click="openWorkspace(novel.id)"
        >
          <div class="recent-top">
            <span class="recent-title">{{ novel.title }}</span>
            <el-tag size="small" effect="plain">{{ formatGenre(novel.genre) }}</el-tag>
          </div>
          <div class="recent-meta">
            最近更新 {{ formatDate(novel.updated_at) }}
          </div>
          <div class="recent-progress">
            第 {{ novel.chapter_count || 0 }} 章 · {{ formatNumber(novel.current_word_count) }} 字
          </div>
          <div class="risk-badge-row">
            <span class="risk-badge" :class="getTaskRiskTone(novel.id).className">{{ getTaskRiskTone(novel.id).label }}</span>
          </div>
          <div class="recent-risk" :class="{ warning: hasTaskRisk(novel.id) }">
            {{ getTaskRiskText(novel.id) }}
          </div>
          <div class="recent-actions">
            <span @click.stop="openWorkspace(novel.id)">继续工作台</span>
            <span v-if="getTaskSummary(novel.id).failed > 0" class="warning-link" @click.stop="openWorkspace(novel.id, { section: 'tasks' })">失败任务</span>
            <span @click.stop="openWorkspace(novel.id, { section: 'overview' })">概览</span>
            <span @click.stop="openWorkspace(novel.id, { section: 'structure' })">结构</span>
            <span @click.stop="openWorkspace(novel.id, { section: 'chapters' })">章节</span>
            <span @click.stop="openWorkspace(novel.id, { section: 'tasks' })">任务</span>
          </div>
        </button>
      </div>
    </section>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="novels.length === 0" class="empty-container">
      <el-empty description="还没有小说，先导入一本或从新书开始。">
        <div class="empty-actions">
          <el-button type="primary" @click="$router.push('/import')">导入小说</el-button>
          <el-button plain @click="$router.push('/config')">先配置模型</el-button>
        </div>
      </el-empty>
    </div>

    <section v-else class="dashboard-section">
      <div class="section-heading">
        <div>
          <h2>我的小说</h2>
          <p>每张卡片都是工作入口，而不是详情跳板。</p>
        </div>
      </div>

      <div class="card-list">
        <article
          v-for="novel in novels"
          :key="novel.id"
          class="novel-card"
          @click="openWorkspace(novel.id)"
        >
          <div class="card-top">
            <div>
              <h3 class="novel-title">{{ novel.title }}</h3>
              <p class="novel-author">作者：{{ novel.author || '未知作者' }}</p>
            </div>
            <el-tag size="small" effect="plain">{{ formatGenre(novel.genre) }}</el-tag>
          </div>

          <div class="card-progress-row">
            <span class="progress-label">完成度</span>
            <span class="progress-value">{{ getProgress(novel) }}%</span>
          </div>
          <el-progress
            :percentage="getProgress(novel)"
            :stroke-width="6"
            :show-text="false"
          />

          <div class="novel-stats">
            <div class="stat-item">
              <span class="stat-label">章节</span>
              <span class="stat-value">{{ novel.chapter_count || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">当前字数</span>
              <span class="stat-value">{{ formatNumber(novel.current_word_count) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">目标字数</span>
              <span class="stat-value">{{ formatNumber(novel.target_word_count) }}</span>
            </div>
          </div>

          <div class="novel-meta-row">
            <span>{{ formatStatus(novel.status) }}</span>
            <span>{{ formatDate(novel.updated_at) }}</span>
          </div>
          <div class="risk-badge-row">
            <span class="risk-badge" :class="getTaskRiskTone(novel.id).className">{{ getTaskRiskTone(novel.id).label }}</span>
          </div>
          <div class="novel-risk-row" :class="{ warning: hasTaskRisk(novel.id) }">
            {{ getTaskRiskText(novel.id) }}
          </div>

          <div class="novel-actions">
            <el-button type="primary" @click.stop="openWorkspace(novel.id)">
              <el-icon><Edit /></el-icon>
              进入工作台
            </el-button>
            <el-button
              v-if="getTaskSummary(novel.id).failed > 0"
              plain
              @click.stop="openWorkspace(novel.id, { section: 'tasks' })"
            >
              失败任务
            </el-button>
            <el-button plain @click.stop="openWorkspace(novel.id, { section: 'overview' })">概览</el-button>
            <el-button plain @click.stop="openWorkspace(novel.id, { section: 'structure' })">结构</el-button>
            <el-button plain @click.stop="openWorkspace(novel.id, { section: 'tasks' })">任务</el-button>
            <el-button plain @click.stop="handleDelete(novel)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { novelApi, projectApi } from '@/api'
import { useRouter } from 'vue-router'

const novels = ref([])
const loading = ref(true)
const taskSummaryByNovel = ref({})
const router = useRouter()
const statusLabelMap = {
  active: '创作中',
  archived: '已归档',
  draft: '草稿'
}
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

const loadNovels = async () => {
  try {
    novels.value = await novelApi.list()
    await loadTaskSummaries(novels.value)
  } catch (error) {
    console.error('加载小说列表失败:', error)
  } finally {
    loading.value = false
  }
}

const buildTaskSummary = (tasks) => {
  const list = Array.isArray(tasks) ? tasks : []
  return {
    all: list.length,
    failed: list.filter((item) => ['failed', 'error'].includes(String(item?.status || '').trim())).length,
    running: list.filter((item) => String(item?.status || '').trim() === 'running').length,
    audit: list.filter((item) => String(item?.task_type || item?.type || '').toLowerCase().includes('audit')).length
  }
}

const loadTaskSummaries = async (items) => {
  const novelsToInspect = [...(items || [])]
    .sort((a, b) => {
      const aTs = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const bTs = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return bTs - aTs
    })
    .slice(0, 6)

  const entries = await Promise.all(novelsToInspect.map(async (novel) => {
    try {
      const project = await projectApi.getByNovel(novel.id).catch(() => null)
      if (!project?.id) {
        return [novel.id, buildTaskSummary([])]
      }
      const tasks = await projectApi.chapterTasksV2(project.id).catch(() => [])
      return [novel.id, buildTaskSummary(tasks)]
    } catch (error) {
      return [novel.id, buildTaskSummary([])]
    }
  }))

  taskSummaryByNovel.value = Object.fromEntries(entries)
}

const getTaskSummary = (novelId) => (
  taskSummaryByNovel.value[novelId] || { all: 0, failed: 0, running: 0, audit: 0 }
)

const getTaskRiskText = (novelId) => {
  const summary = getTaskSummary(novelId)
  if (summary.failed > 0) return `${summary.failed} 个失败任务`
  if (summary.running > 0) return `${summary.running} 个运行中任务`
  if (summary.audit > 0) return `${summary.audit} 个审查任务`
  if (summary.all > 0) return `${summary.all} 个项目任务`
  return '当前无明显任务风险'
}

const hasTaskRisk = (novelId) => getTaskSummary(novelId).failed > 0 || getTaskSummary(novelId).running > 0

const getTaskRiskTone = (novelId) => {
  const summary = getTaskSummary(novelId)
  if (summary.failed > 0) return { label: '高优先级', className: 'danger' }
  if (summary.running > 0) return { label: '处理中', className: 'running' }
  return { label: '稳定', className: 'normal' }
}

const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num?.toLocaleString() || '0'
}

const getProgress = (novel) => {
  if (!novel.target_word_count) return 0
  return Math.min(100, Math.round((novel.current_word_count / novel.target_word_count) * 100))
}

const formatGenre = (genre) => genreMap[genre] || genre || '未知'
const formatStatus = (status) => statusLabelMap[status] || status || '进行中'

const formatDate = (value) => {
  if (!value) return '最近未更新'
  try {
    return new Date(value).toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric'
    })
  } catch (error) {
    return '最近未更新'
  }
}

const sortedNovels = computed(() => {
  return [...novels.value].sort((a, b) => {
    const aTs = a.updated_at ? new Date(a.updated_at).getTime() : 0
    const bTs = b.updated_at ? new Date(b.updated_at).getTime() : 0
    return bTs - aTs
  })
})

const recentNovels = computed(() => sortedNovels.value.slice(0, 3))
const featuredNovel = computed(() => recentNovels.value[0] || null)
const activeNovelCount = computed(() => novels.value.filter((item) => item.status !== 'archived').length)
const totalChapterCount = computed(() => novels.value.reduce((sum, item) => sum + Number(item.chapter_count || 0), 0))

const openWorkspace = (novelId, query = {}) => {
  router.push({
    path: `/novel/${novelId}`,
    query
  })
}

const handleDelete = async (novel) => {
  try {
    await ElMessageBox.confirm(`确定要删除小说《${novel.title}》吗？`, '确认删除', {
      type: 'warning'
    })
    await novelApi.delete(novel.id)
    ElMessage.success('删除成功')
    loadNovels()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

onMounted(() => {
  loadNovels()
})
</script>

<style scoped>
.novel-list {
  max-width: 1360px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

.dashboard-hero {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 20px;
  padding: 28px;
  border: 1px solid #E5E7EB;
  border-radius: 24px;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.hero-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hero-eyebrow {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hero-title {
  font-size: 34px;
  line-height: 1.2;
  font-weight: 600;
  color: #111827;
}

.hero-description {
  max-width: 720px;
  font-size: 15px;
  line-height: 1.8;
  color: #4B5563;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.hero-side {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.hero-featured-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid #DBEAFE;
  background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
}

.featured-label {
  font-size: 11px;
  font-weight: 600;
  color: #2563EB;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.featured-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.featured-meta {
  font-size: 13px;
  color: #4B5563;
}

.featured-risk,
.recent-risk,
.novel-risk-row {
  font-size: 12px;
  color: #6B7280;
}

.risk-badge-row {
  margin-top: 10px;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid #E5E7EB;
  background-color: #F9FAFB;
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
}

.risk-badge.danger {
  border-color: #FECACA;
  background-color: #FEF2F2;
  color: #B91C1C;
}

.risk-badge.running {
  border-color: #BFDBFE;
  background-color: #EFF6FF;
  color: #1D4ED8;
}

.risk-badge.normal {
  border-color: #D1FAE5;
  background-color: #ECFDF5;
  color: #047857;
}

.featured-risk.warning,
.recent-risk.warning,
.novel-risk-row.warning {
  color: #B45309;
}

.featured-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.featured-action {
  border: 1px solid #BFDBFE;
  background-color: #FFFFFF;
  color: #1D4ED8;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.featured-action.primary {
  background-color: #1D4ED8;
  border-color: #1D4ED8;
  color: #FFFFFF;
}

.featured-action.warning {
  border-color: #FCD34D;
  background-color: #FFFBEB;
  color: #B45309;
}

.hero-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
}

.hero-stat-label {
  font-size: 12px;
  color: #9CA3AF;
}

.hero-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.dashboard-section {
  margin-top: 28px;
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-heading h2 {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.section-heading p {
  margin-top: 6px;
  font-size: 14px;
  color: #6B7280;
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.loading-container,
.empty-container {
  padding: 72px 20px;
  text-align: center;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.recent-card,
.novel-card {
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  border-radius: 20px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.22s ease;
}

.recent-card:hover,
.novel-card:hover {
  transform: translateY(-2px);
  border-color: #D1D5DB;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.recent-card {
  text-align: left;
}

.recent-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.recent-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.recent-meta,
.recent-progress {
  margin-top: 10px;
  font-size: 13px;
  color: #6B7280;
  line-height: 1.6;
}

.recent-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #2563EB;
}

.warning-link {
  color: #B45309;
}

.recent-risk {
  margin-top: 8px;
}

.card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 18px;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.novel-title {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  line-height: 1.35;
}

.novel-author {
  margin-top: 8px;
  font-size: 13px;
  color: #6B7280;
}

.card-progress-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label,
.progress-value {
  font-size: 12px;
  color: #6B7280;
}

.progress-value {
  font-weight: 600;
  color: #111827;
}

.novel-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: 14px;
  background-color: #F9FAFB;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.stat-label {
  font-size: 12px;
  color: #9CA3AF;
}

.novel-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  font-size: 12px;
  color: #6B7280;
}

.novel-risk-row {
  margin-top: 10px;
}

.novel-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  margin-top: 18px;
}

@media (max-width: 1100px) {
  .dashboard-hero,
  .recent-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero-actions,
  .empty-actions,
  .novel-actions {
    flex-direction: column;
  }

  .novel-stats {
    grid-template-columns: 1fr;
  }
}
</style>
