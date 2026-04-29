<template>
  <div class="works-page">
    <section class="hero-panel">
      <div class="hero-copy">
        <div class="hero-eyebrow">书架</div>
        <h1 class="hero-title">选择作品，开始写作</h1>
        <p class="hero-description">支持新建作品或导入 TXT，进入后即可继续创作。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="createWork" :loading="creating">
          <el-icon><Plus /></el-icon>
          新建作品
        </el-button>
        <el-button plain @click="showImportModal = true">
          <el-icon><Upload /></el-icon>
          导入 TXT
        </el-button>
      </div>
    </section>

    <section class="summary-panel">
      <div class="summary-card">
        <span class="summary-label">作品总数</span>
        <span class="summary-value">{{ works.length }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">总字数</span>
        <span class="summary-value">{{ formatNumber(totalWords) }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">最近作品</span>
        <span class="summary-value">{{ latestWork?.title || '暂无' }}</span>
      </div>
    </section>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="4" animated />
    </div>

    <section v-else-if="errorMessage" class="error-panel">
      <h2>书架加载失败</h2>
      <p>{{ errorMessage }}</p>
      <div class="error-actions">
        <el-button type="primary" @click="loadWorks">重新加载</el-button>
        <el-button plain @click="createWork" :loading="creating">先新建作品</el-button>
      </div>
    </section>

    <div v-else-if="works.length === 0" class="empty-container">
      <el-empty description="书架还是空的，先创建一个作品开始写作。">
        <div class="empty-hint">你可以先新建空白作品，也可以直接导入现有 TXT 稿件。</div>
        <div class="empty-actions">
          <el-button type="primary" @click="createWork" :loading="creating">新建作品</el-button>
          <el-button plain @click="showImportModal = true">导入 TXT</el-button>
        </div>
      </el-empty>
    </div>

    <section v-else class="works-section">
      <div class="section-heading">
        <div>
          <h2>我的作品</h2>
          <p>点击作品卡片即可打开。</p>
        </div>
      </div>

      <div class="works-grid">
        <WorkCard
          v-for="work in works"
          :key="work.id"
          :work="work"
          @open="openWorkspace"
        />
      </div>
    </section>

    <ImportModal
      v-model="showImportModal"
      @imported="handleImported"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'
import { v1WorksApi } from '@/api'
import { useRouter } from 'vue-router'
import WorkCard from '@/components/works/WorkCard.vue'
import ImportModal from '@/components/works/ImportModal.vue'

const router = useRouter()
const works = ref([])
const loading = ref(true)
const creating = ref(false)
const showImportModal = ref(false)
const errorMessage = ref('')

const loadWorks = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await v1WorksApi.list()
    works.value = Array.isArray(response?.items) ? response.items : []
  } catch (error) {
    console.error('加载作品列表失败:', error)
    works.value = []
    errorMessage.value = '暂时无法读取作品列表，请检查后端服务是否已启动。'
  } finally {
    loading.value = false
  }
}

const createWork = async () => {
  if (creating.value) return
  creating.value = true
  try {
    const created = await v1WorksApi.create({
      title: buildDraftTitle(),
      author: ''
    })
    ElMessage.success('已创建新作品')
    await loadWorks()
    openWorkspace(created.id)
  } catch (error) {
    console.error('创建作品失败:', error)
    ElMessage.error('创建作品失败，请稍后重试。')
  } finally {
    creating.value = false
  }
}

const handleImported = async (work) => {
  await loadWorks()
  if (work?.id) {
    openWorkspace(work.id)
  }
}

const openWorkspace = (workId) => {
  router.push({
    path: `/works/${workId}`
  })
}

const buildDraftTitle = () => {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `未命名作品 ${month}${day}`
}

const formatNumber = (num) => Number(num || 0).toLocaleString('zh-CN')

const totalWords = computed(() => works.value.reduce((sum, item) => sum + Number(item.current_word_count || 0), 0))
const latestWork = computed(() => works.value[0] || null)

onMounted(() => {
  loadWorks()
})
</script>

<style scoped>
.works-page {
  max-width: 1360px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

.hero-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.hero-copy {
  max-width: 720px;
}

.hero-eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b7280;
}

.hero-title {
  margin-top: 10px;
  font-size: 34px;
  line-height: 1.2;
  font-weight: 700;
  color: #111827;
}

.hero-description {
  margin-top: 12px;
  font-size: 15px;
  line-height: 1.8;
  color: #4b5563;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.summary-panel {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  background-color: #ffffff;
}

.summary-label {
  font-size: 12px;
  color: #9ca3af;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

.loading-container,
.empty-container {
  padding: 72px 20px;
  text-align: center;
}

.error-panel {
  margin-top: 28px;
  padding: 28px;
  border: 1px solid #fecaca;
  border-radius: 24px;
  background: #fff7f7;
}

.error-panel h2 {
  font-size: 20px;
  font-weight: 600;
  color: #991b1b;
}

.error-panel p {
  margin-top: 10px;
  font-size: 14px;
  color: #7f1d1d;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

.empty-hint {
  margin-bottom: 14px;
  font-size: 13px;
  color: #6b7280;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.works-section {
  margin-top: 28px;
}

.section-heading {
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
  color: #6b7280;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 18px;
}

@media (max-width: 960px) {
  .hero-panel,
  .summary-panel {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .hero-actions,
  .empty-actions,
  .error-actions {
    width: 100%;
    flex-direction: column;
  }

  .summary-panel {
    grid-template-columns: 1fr;
  }
}
</style>
