<template>
  <div class="novel-list">
    <div class="page-header">
      <h2 class="page-title">我的小说</h2>
      <el-button type="primary" @click="$router.push('/import')">
        <el-icon><Plus /></el-icon>
        导入新小说
      </el-button>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="novels.length === 0" class="empty-container">
      <el-empty description="还没有小说，点击上方按钮导入">
        <el-button type="primary" @click="$router.push('/import')">导入小说</el-button>
      </el-empty>
    </div>

    <div v-else class="card-list">
      <el-card
        v-for="novel in novels"
        :key="novel.id"
        class="novel-card"
        shadow="hover"
        @click="$router.push(`/novel/${novel.id}/workspace/overview`)"
      >
        <div class="novel-info">
          <h3 class="novel-title">{{ novel.title }}</h3>
          <p class="novel-author">作者：{{ novel.author || '未知' }}</p>
          <el-tag size="small" type="info">{{ formatGenre(novel.genre) }}</el-tag>
        </div>

        <div class="novel-stats">
          <div class="stat-item">
            <span class="stat-value">{{ formatNumber(novel.current_word_count) }}</span>
            <span class="stat-label">当前字数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ formatNumber(novel.target_word_count) }}</span>
            <span class="stat-label">目标字数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ novel.chapter_count }}</span>
            <span class="stat-label">章节数</span>
          </div>
        </div>

        <div class="novel-progress">
          <el-progress
            :percentage="getProgress(novel)"
            :stroke-width="8"
            :show-text="false"
          />
          <span class="progress-text">完成度 {{ getProgress(novel) }}%</span>
        </div>

        <div class="novel-actions">
          <el-button type="primary" size="small" @click.stop="$router.push(`/novel/${novel.id}/workspace/writing`)">
            <el-icon><Edit /></el-icon>
            续写
          </el-button>
          <el-button size="small" @click.stop="handleDelete(novel)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { novelApi } from '@/api'

const novels = ref([])
const loading = ref(true)
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
  } catch (error) {
    console.error('加载小说列表失败:', error)
  } finally {
    loading.value = false
  }
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
  padding: 20px;
}

.loading-container,
.empty-container {
  padding: 60px 20px;
  text-align: center;
}

.novel-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.novel-card:hover {
  transform: translateY(-4px);
}

.novel-info {
  margin-bottom: 15px;
}

.novel-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.novel-author {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.novel-stats {
  display: flex;
  justify-content: space-around;
  padding: 15px 0;
  border-top: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 15px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.novel-progress {
  margin-bottom: 15px;
}

.progress-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  display: block;
}

.novel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
