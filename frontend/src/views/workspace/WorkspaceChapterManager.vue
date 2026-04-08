<template>
  <div class="workspace-page">
    <section class="workspace-section">
      <div class="section-header">
        <div>
          <h2>章节台</h2>
          <p>先把目录和打开路径稳定下来，后续再升级为看板和拖拽目录树。</p>
        </div>
        <el-button type="primary" @click="workspace.createChapter">新建章节</el-button>
      </div>

      <el-table :data="workspace.state.chapters" border>
        <el-table-column prop="chapter_number" label="章节号" width="100" />
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="workspace.openChapter(row.id)">打开写作台</el-button>
            <el-button size="small" @click="openLegacyEditor(row.id)">旧版编辑器</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

import { useWorkspaceContext } from '@/composables/useWorkspaceContext'

const router = useRouter()
const workspace = useWorkspaceContext()

const formatDate = (value) => {
  if (!value) return '未记录'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch (error) {
    return '未记录'
  }
}

const openLegacyEditor = (chapterId) => {
  router.push(`/novel/${workspace.state.novel?.id}/chapters/${chapterId}/edit`)
}
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.workspace-section {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 34px rgba(93, 72, 37, 0.07);
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-header h2 {
  color: #342318;
}

.section-header p {
  margin-top: 8px;
  color: #6f5641;
  line-height: 1.7;
}
</style>
