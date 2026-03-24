<template>
  <div class="novel-write">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.push(`/novel/${$route.params.id}`)">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2 class="page-title">续写小说</h2>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="write-card">
          <el-alert
            v-if="continueHint"
            :title="continueHint"
            type="success"
            show-icon
            :closable="false"
            style="margin-bottom: 16px;"
          />

          <el-form :model="form" label-width="100px">
            <el-form-item label="剧情方向">
              <el-input
                v-model="form.plot_direction"
                type="textarea"
                :rows="3"
                placeholder="可以输入一句方向提示，例如：主角正式进入宗门外围试炼，并在新环境中暴露异常天赋。"
              />
            </el-form-item>

            <el-form-item label="剧情分支">
              <div class="branch-panel">
                <div class="branch-toolbar">
                  <el-button :loading="branchLoading" @click="generateBranches">生成分支</el-button>
                  <span class="branch-hint">先选分支，再预览或正式写入章节。</span>
                </div>
                <div v-if="!branches.length" class="branch-empty">暂无分支，请先生成。</div>
                <div v-else class="branch-list">
                  <div
                    v-for="item in branches"
                    :key="item.id"
                    class="branch-card"
                    :class="{ active: selectedBranchId === item.id }"
                    @click="selectedBranchId = item.id"
                  >
                    <div class="branch-card-header">
                      <el-radio :model-value="selectedBranchId" :label="item.id" @change="selectedBranchId = item.id">
                        {{ item.title }}
                      </el-radio>
                      <el-tag size="small" type="success" v-if="item.style_tags?.[0]">{{ item.style_tags[0] }}</el-tag>
                    </div>
                    <div class="branch-summary">{{ item.summary }}</div>
                    <div v-if="item.core_conflict" class="branch-meta">
                      <strong>核心冲突：</strong>{{ item.core_conflict }}
                    </div>
                    <div v-if="item.consistency_note" class="branch-meta">
                      <strong>大纲一致性：</strong>{{ item.consistency_note }}
                    </div>
                    <div v-if="item.risk_note" class="branch-meta risk">
                      <strong>风险：</strong>{{ item.risk_note }}
                    </div>
                  </div>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="生成章节数">
              <el-input-number v-model="form.chapter_count" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="每章字数">
              <el-input-number v-model="form.target_word_count" :min="1000" :max="5000" :step="100" />
            </el-form-item>

            <el-form-item label="文风模仿">
              <el-switch v-model="form.enable_style_mimicry" />
              <span class="switch-tip">开启后尽量贴近已有章节风格</span>
            </el-form-item>

            <el-form-item label="连贯性检查">
              <el-switch v-model="form.enable_consistency_check" />
              <span class="switch-tip">开启后更强调人物状态和设定一致性</span>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="generating" @click="generatePreview">
                <el-icon><Edit /></el-icon>
                预览一章
              </el-button>
              <el-button type="success" :loading="generatingNext" @click="continueNextChapter">
                <el-icon><Edit /></el-icon>
                保存并继续生成
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-if="generatedContent" class="result-card">
          <template #header>
            <div class="card-header">
              <span>生成结果</span>
              <div class="result-actions">
                <el-button size="small" @click="copyContent">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button size="small" @click="downloadGeneratedChapter">
                  <el-icon><Download /></el-icon>
                  导出章节
                </el-button>
              </div>
            </div>
          </template>

          <div class="content-info">
            <el-tag>字数：{{ generatedContent.word_count }}</el-tag>
            <el-tag :type="isPersistedResult ? 'success' : 'warning'">
              {{ isPersistedResult ? '已保存到章节列表' : '预览内容，尚未落库' }}
            </el-tag>
          </div>

          <el-divider />

          <div class="content-body">{{ generatedContent.content }}</div>

          <el-divider />

          <div class="content-actions">
            <el-button type="primary" disabled>{{ saveHintLabel }}</el-button>
            <el-button @click="regenerate">重新生成预览</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="tips-card">
          <template #header>
            <span>写作提示</span>
          </template>

          <el-alert
            title="“预览一章”只生成草稿，不写入章节列表；“保存并继续生成”会按计划正式落库。"
            type="info"
            :closable="false"
            style="margin-bottom: 12px;"
          />

          <el-collapse>
            <el-collapse-item title="如何描述剧情方向" name="1">
              <ul>
                <li>写清这几章想推进哪条主线。</li>
                <li>可以指定人物关系、节奏和冲突。</li>
                <li>如果不填，也可以直接选系统生成的分支。</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="为什么先选分支" name="2">
              <ul>
                <li>分支是后续剧情方案。</li>
                <li>选中后再生成章节，能减少正文跑偏。</li>
                <li>正式生成前先预览一章会更稳。</li>
              </ul>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <span>最近章节</span>
          </template>

          <el-scrollbar height="260px">
            <div v-for="chapter in recentChapters" :key="chapter.id" class="chapter-item">
              <span>第{{ chapter.number }}章 {{ chapter.title }}</span>
              <span class="chapter-words">{{ chapter.word_count }}字</span>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { novelApi, projectApi } from '@/api'

const route = useRoute()
const generating = ref(false)
const generatingNext = ref(false)
const branchLoading = ref(false)
const generatedContent = ref(null)
const recentChapters = ref([])
const continueHint = ref('')
const branches = ref([])
const selectedBranchId = ref('')
const projectId = ref('')

const form = reactive({
  plot_direction: '',
  chapter_count: 1,
  target_word_count: 2100,
  enable_style_mimicry: true,
  enable_consistency_check: true
})

const selectedBranch = computed(() => branches.value.find((item) => item.id === selectedBranchId.value) || null)

const isPersistedResult = computed(() => {
  const routeName = generatedContent.value?.metadata?.route
  return ['continue_tool', 'first_chapter', 'v2_write', 'v2_workflow'].includes(routeName)
})

const saveHintLabel = computed(() => (isPersistedResult.value ? '已保存到章节列表' : '预览内容，尚未保存'))

const resolveDirection = () => {
  if (selectedBranch.value) {
    const pieces = [
      selectedBranch.value.title,
      selectedBranch.value.summary,
      selectedBranch.value.core_conflict
    ].filter(Boolean)
    return pieces.join('；')
  }
  return form.plot_direction
}

const ensureProjectId = async () => {
  if (!projectId.value) {
    const project = await projectApi.getByNovel(route.params.id)
    projectId.value = project?.id || ''
  }
  if (!projectId.value) {
    throw new Error('项目不存在，无法继续创作')
  }
}

const generateBranches = async () => {
  try {
    branchLoading.value = true
    await ensureProjectId()
    const result = await projectApi.branchesV2(projectId.value, {
      direction_hint: form.plot_direction || '',
      branch_count: 4
    })
    branches.value = result.branches || []
    if (branches.value.length > 0) {
      selectedBranchId.value = branches.value[0].id
      if (!form.plot_direction) {
        form.plot_direction = `${branches.value[0].title}：${branches.value[0].summary}`
      }
    }
  } catch (error) {
    console.error('生成分支失败:', error)
  } finally {
    branchLoading.value = false
  }
}

const generatePreview = async () => {
  const direction = resolveDirection()
  if (!direction) {
    ElMessage.warning('请先生成并选择剧情分支，或手动填写剧情方向')
    return
  }

  try {
    generating.value = true
    ElMessage.info('正在生成预览章节...')
    await ensureProjectId()
    if (!selectedBranchId.value) {
      throw new Error('请先生成并选择剧情分支')
    }
    const planResult = await projectApi.chapterPlanV2(projectId.value, {
      branch_id: selectedBranchId.value,
      chapter_count: 1,
      target_words_per_chapter: form.target_word_count
    })
    const planIds = (planResult.plans || []).map((plan) => plan.id)
    const writeResult = await projectApi.writeV2(projectId.value, {
      plan_ids: planIds,
      auto_commit: false
    })
    const content = writeResult?.latest_content || ''
    generatedContent.value = {
      content,
      word_count: content.length,
      metadata: { route: 'v2_preview' }
    }
    ElMessage.success('预览已生成，尚未保存到章节列表')
  } catch (error) {
    console.error('生成预览失败:', error)
  } finally {
    generating.value = false
  }
}

const continueNextChapter = async () => {
  const direction = resolveDirection()
  if (!direction) {
    ElMessage.warning('请先生成并选择剧情分支，或手动填写剧情方向')
    return
  }

  try {
    generatingNext.value = true
    ElMessage.info('正在按计划生成并保存章节...')
    await ensureProjectId()
    if (!selectedBranchId.value) {
      throw new Error('请先生成并选择剧情分支')
    }

    const currentLatestChapter = recentChapters.value.length ? recentChapters.value[0].number : 0
    const fromChapterNumber = currentLatestChapter + 1

    const planResult = await projectApi.chapterPlanV2(projectId.value, {
      branch_id: selectedBranchId.value,
      chapter_count: form.chapter_count,
      target_words_per_chapter: form.target_word_count
    })
    const planIds = (planResult.plans || []).map((plan) => plan.id)
    await projectApi.writeV2(projectId.value, {
      plan_ids: planIds,
      auto_commit: true
    })
    await projectApi.refreshMemoryV2(projectId.value, {
      from_chapter_number: fromChapterNumber,
      to_chapter_number: fromChapterNumber + form.chapter_count - 1
    })

    const latestNovel = await novelApi.get(route.params.id)
    const latest = latestNovel.chapters?.[latestNovel.chapters.length - 1]
    generatedContent.value = {
      content: latest?.content || '',
      word_count: latest?.word_count || (latest?.content || '').length,
      metadata: { route: 'v2_write' }
    }

    await loadRecentChapters()
    await generateBranches()
    ElMessage.success('章节已生成并保存，分支也已基于最新内容刷新')
  } catch (error) {
    console.error('继续生成失败:', error)
  } finally {
    generatingNext.value = false
  }
}

const copyContent = () => {
  if (!generatedContent.value?.content) return
  navigator.clipboard.writeText(generatedContent.value.content)
  ElMessage.success('已复制到剪贴板')
}

const downloadGeneratedChapter = () => {
  if (!generatedContent.value?.content) return
  const chapterNumber = recentChapters.value.length ? recentChapters.value[0].number + (isPersistedResult.value ? 0 : 1) : 1
  const title = `第${chapterNumber}章`
  const blob = new Blob([`# ${title}\n\n${generatedContent.value.content}\n`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${title}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('章节已导出')
}

const regenerate = () => {
  generatedContent.value = null
  generatePreview()
}

const loadRecentChapters = async () => {
  try {
    const novel = await novelApi.get(route.params.id)
    recentChapters.value = novel.chapters?.slice(-5).reverse() || []
    if (!form.plot_direction) {
      const nextChapterNumber = (novel.chapter_count || 0) + 1
      form.plot_direction = route.query.default_goal || `第${nextChapterNumber}章承接上一章主线继续推进`
    }
  } catch (error) {
    console.error('加载最近章节失败:', error)
  }
}

const initPage = async () => {
  if (route.query.auto_continue === '1') {
    continueHint.value = '已生成第一章，是否继续创作下一章？'
  }

  const raw = sessionStorage.getItem('inktrace_continue_hint')
  if (raw) {
    try {
      const hint = JSON.parse(raw)
      if (hint?.novelId === route.params.id) {
        continueHint.value = hint.message || continueHint.value
        if (hint.firstChapter?.content) {
          generatedContent.value = {
            content: hint.firstChapter.content,
            word_count: hint.firstChapter.word_count || hint.firstChapter.content.length,
            metadata: { route: 'first_chapter' }
          }
        }
      }
    } finally {
      sessionStorage.removeItem('inktrace_continue_hint')
    }
  }

  await loadRecentChapters()
  await generateBranches()
}

onMounted(() => {
  initPage()
})
</script>

<style scoped>
.novel-write {
  padding: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.write-card,
.result-card,
.tips-card,
.history-card {
  margin-bottom: 20px;
}

.switch-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-actions {
  display: flex;
  gap: 8px;
}

.content-info {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.content-body {
  white-space: pre-wrap;
  line-height: 1.8;
  max-height: 420px;
  overflow-y: auto;
}

.content-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.chapter-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
  font-size: 14px;
}

.chapter-words {
  color: #909399;
  font-size: 12px;
}

.branch-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.branch-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.branch-hint {
  font-size: 12px;
  color: #909399;
}

.branch-empty {
  color: #909399;
  font-size: 13px;
}

.branch-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.branch-card {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.branch-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.08);
}

.branch-card.active {
  border-color: #409eff;
  background: #f5f9ff;
}

.branch-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.branch-summary {
  margin-top: 8px;
  line-height: 1.7;
  color: #303133;
}

.branch-meta {
  margin-top: 6px;
  line-height: 1.6;
  color: #606266;
  font-size: 13px;
}

.branch-meta.risk {
  color: #c45656;
}
</style>
