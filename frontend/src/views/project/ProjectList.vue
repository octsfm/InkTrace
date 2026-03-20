<template>
  <div class="project-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>项目管理</span>
          <el-button type="primary" @click="showCreateDialog">新建项目</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="projects">
        <el-table-column prop="name" label="项目名称" />
        <el-table-column prop="genre" label="题材">
          <template #default="{ row }">
            <el-tag>{{ genreMap[row.genre] || row.genre }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_words" label="目标字数">
          <template #default="{ row }">
            {{ (row.target_words / 10000).toFixed(0) }}万字
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '创作中' : '已归档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="enterProject(row)">进入</el-button>
            <el-button v-if="row.status === 'active'" size="small" type="warning" @click="archiveProject(row)">归档</el-button>
            <el-button size="small" type="danger" @click="deleteProject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="创建小说" width="620px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="题材类型">
          <el-select v-model="createForm.genre" placeholder="选择题材">
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
        <el-form-item label="目标字数">
          <el-input-number v-model="createForm.target_words" :min="100000" :max="50000000" :step="100000" />
          <span style="margin-left: 10px;">{{ (createForm.target_words / 10000).toFixed(0) }}万字</span>
        </el-form-item>
        <el-form-item label="风格" required>
          <el-input v-model="createForm.style" placeholder="如：热血、悬疑、克制、轻松" />
        </el-form-item>
        <el-form-item label="主角设定" required>
          <el-input
            v-model="createForm.protagonist_setting"
            type="textarea"
            :rows="3"
            placeholder="如：林渊，十七岁，冷静坚韧，背负家族秘密"
          />
        </el-form-item>
        <el-form-item label="世界观">
          <el-input
            v-model="createForm.worldview"
            type="textarea"
            :rows="3"
            placeholder="可选，如：灵气复苏后的多势力世界"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createProject">
          {{ creating ? '正在创作...' : '创建并生成' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()
const projects = ref([])
const loading = ref(false)
const createDialogVisible = ref(false)
const creating = ref(false)

const createForm = ref({
  name: '',
  genre: 'xuanhuan',
  target_words: 8000000
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

const loadProjects = async () => {
  loading.value = true
  try {
    const res = await api.get('/projects')
    projects.value = res
  } catch (error) {
    console.error('加载项目列表失败:', error)
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  createForm.value = {
    name: '',
    genre: 'xuanhuan',
    target_words: 8000000,
    style: '',
    protagonist_setting: '',
    worldview: ''
  }
  createDialogVisible.value = true
}

const createProject = async () => {
  if (!createForm.value.name || !createForm.value.style || !createForm.value.protagonist_setting) {
    ElMessage.warning('请填写名称、风格和主角设定')
    return
  }
  creating.value = true
  try {
    const res = await api.post('/projects', createForm.value)
    createDialogVisible.value = false
    sessionStorage.setItem(
      'inktrace_continue_hint',
      JSON.stringify({
        novelId: res?.project?.novel_id,
        message: '已生成第一章，是否继续创作第二章？',
        defaultGoal: '第2章：承接第一章并推进主线',
        firstChapter: res?.first_chapter || null
      })
    )
    ElMessage.success('创建完成，正在进入创作...')
    await loadProjects()
    if (res?.project?.novel_id) {
      router.push(`/novel/${res.project.novel_id}/write?auto_continue=1&default_goal=${encodeURIComponent('第2章：承接第一章并推进主线')}`)
    }
  } catch (error) {
    console.error('创建项目失败:', error)
  } finally {
    creating.value = false
  }
}

const enterProject = (project) => {
  if (!project) return
  router.push(`/novel/${project.novel_id}`)
}

const archiveProject = async (project) => {
  try {
    await api.post(`/projects/${project.id}/archive`)
    loadProjects()
  } catch (error) {
    console.error('归档失败:', error)
  }
}

const deleteProject = async (project) => {
  try {
    await api.delete(`/projects/${project.id}`)
    loadProjects()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.project-list {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
