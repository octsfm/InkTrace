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
                  <div class="branch-toolbar-left">
                    <el-button :loading="branchLoading" @click="generateBranches">生成分支</el-button>
                    <el-button @click="openStyleDialog">风格要求</el-button>
                  </div>
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
            <el-tag type="info">章节：第{{ generatedContent.chapter_number || '-' }}章 {{ generatedContent.title || '未命名章节' }}</el-tag>
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

          <el-divider />

          <div v-if="draftCompare.structural.content || draftCompare.detemplated.content" class="draft-compare">
            <div class="compare-header">
              <span>草稿对比</span>
              <el-tag :type="draftCompare.usedStructuralFallback ? 'warning' : 'success'">
                {{ draftCompare.usedStructuralFallback ? '已回退结构稿' : '去模板稿生效' }}
              </el-tag>
            </div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-card shadow="never">
                  <template #header>结构稿</template>
                  <div class="compare-title">{{ draftCompare.structural.title || '未命名' }}</div>
                  <div class="compare-body">{{ draftCompare.structural.content || '暂无' }}</div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card shadow="never">
                  <template #header>去模板稿</template>
                  <div class="compare-title">{{ draftCompare.detemplated.title || '未命名' }}</div>
                  <div class="compare-body">{{ draftCompare.detemplated.content || '暂无' }}</div>
                </el-card>
              </el-col>
            </el-row>
            <div v-if="draftCompare.integrity.risk_notes?.length" class="risk-notes">
              <el-tag type="warning">校验风险</el-tag>
              <ul>
                <li v-for="(item, index) in draftCompare.integrity.risk_notes" :key="`risk-${index}`">{{ item }}</li>
              </ul>
            </div>
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
              <div class="chapter-actions">
                <span class="chapter-words">{{ chapter.word_count }}字</span>
                <el-button type="danger" link size="small" :loading="deletingChapterId === chapter.id" @click="deleteRecentChapter(chapter)">
                  删除
                </el-button>
              </div>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="styleDialogVisible" title="风格要求" width="620px">
      <el-form label-width="110px">
        <el-form-item label="作者风格关键词">
          <el-select v-model="styleForm.author_voice_keywords" multiple allow-create filterable default-first-option style="width: 100%" />
        </el-form-item>
        <el-form-item label="避免表达模式">
          <el-select v-model="styleForm.avoid_patterns" multiple allow-create filterable default-first-option style="width: 100%" />
        </el-form-item>
        <el-form-item label="偏好节奏">
          <el-input v-model="styleForm.preferred_rhythm" placeholder="例如：中速节奏、快节奏" />
        </el-form-item>
        <el-form-item label="叙事距离">
          <el-input v-model="styleForm.narrative_distance" placeholder="例如：第一人称/第三人称有限视角" />
        </el-form-item>
        <el-form-item label="对话密度">
          <el-input v-model="styleForm.dialogue_density" placeholder="高/中/低" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :loading="styleLoading" @click="extractStyleRequirements">从最近样章提取</el-button>
        <el-button @click="styleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="styleSaving" @click="saveStyleRequirements">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const deletingChapterId = ref('')
const styleDialogVisible = ref(false)
const styleLoading = ref(false)
const styleSaving = ref(false)
const draftCompare = ref({
  structural: {},
  detemplated: {},
  integrity: {},
  usedStructuralFallback: false
})
const styleForm = reactive({
  author_voice_keywords: [],
  avoid_patterns: [],
  preferred_rhythm: '',
  narrative_distance: '',
  dialogue_density: ''
})

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
    draftCompare.value = {
      structural: writeResult?.latest_structural_draft || {},
      detemplated: writeResult?.latest_detemplated_draft || {},
      integrity: writeResult?.latest_draft_integrity_check || {},
      usedStructuralFallback: !!writeResult?.used_structural_fallback
    }
    const chapter = writeResult?.latest_chapter || {}
    const content = chapter.content || writeResult?.latest_content || ''
    const title = chapter.title || writeResult?.latest_title || `第${chapter.number || (recentChapters.value[0]?.number || 0) + 1}章`
    const chapterNumber = chapter.number || writeResult?.latest_chapter_number || ((recentChapters.value[0]?.number || 0) + 1)
    generatedContent.value = {
      title,
      chapter_number: chapterNumber,
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

    const planResult = await projectApi.chapterPlanV2(projectId.value, {
      branch_id: selectedBranchId.value,
      chapter_count: form.chapter_count,
      target_words_per_chapter: form.target_word_count
    })
    const planIds = (planResult.plans || []).map((plan) => plan.id)
    const writeResult = await projectApi.writeV2(projectId.value, {
      plan_ids: planIds,
      auto_commit: true
    })
    draftCompare.value = {
      structural: writeResult?.latest_structural_draft || {},
      detemplated: writeResult?.latest_detemplated_draft || {},
      integrity: writeResult?.latest_draft_integrity_check || {},
      usedStructuralFallback: !!writeResult?.used_structural_fallback
    }
    const generatedIds = writeResult?.generated_chapter_ids || []
    const latestChapterNumber = Number(writeResult?.latest_chapter_number || 0)
    const fromChapterNumber = latestChapterNumber > 0 ? Math.max(1, latestChapterNumber - generatedIds.length + 1) : 1
    const toChapterNumber = latestChapterNumber > 0 ? latestChapterNumber : (fromChapterNumber + Math.max(form.chapter_count, 1) - 1)
    await projectApi.refreshMemoryV2(projectId.value, {
      from_chapter_number: fromChapterNumber,
      to_chapter_number: toChapterNumber
    })

    const latestNovel = await novelApi.get(route.params.id)
    const latest = latestNovel.chapters?.[latestNovel.chapters.length - 1]
    generatedContent.value = {
      title: latest?.title || writeResult?.latest_title || `第${latest?.number || latestChapterNumber || 0}章`,
      chapter_number: latest?.number || latestChapterNumber || 0,
      content: latest?.content || '',
      word_count: latest?.word_count || (latest?.content || '').length,
      metadata: { route: 'v2_write' }
    }

    await loadRecentChapters()
    ElMessage.success('章节已生成并保存，可手动重新生成分支')
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
  const chapterNumber = generatedContent.value.chapter_number || (recentChapters.value.length ? recentChapters.value[0].number + (isPersistedResult.value ? 0 : 1) : 0)
  const chapterTitle = generatedContent.value.title || (chapterNumber > 0 ? `第${chapterNumber}章` : '生成章节')
  const blob = new Blob([`# ${chapterTitle}\n\n${generatedContent.value.content}\n`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${chapterTitle}.md`
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

const loadStyleRequirements = async () => {
  try {
    await ensureProjectId()
    const payload = await projectApi.getStyleRequirements(projectId.value)
    const req = payload?.style_requirements || {}
    styleForm.author_voice_keywords = req.author_voice_keywords || []
    styleForm.avoid_patterns = req.avoid_patterns || []
    styleForm.preferred_rhythm = req.preferred_rhythm || ''
    styleForm.narrative_distance = req.narrative_distance || ''
    styleForm.dialogue_density = req.dialogue_density || ''
  } catch (error) {
    console.error('加载风格要求失败:', error)
  }
}

const openStyleDialog = async () => {
  await loadStyleRequirements()
  styleDialogVisible.value = true
}

const saveStyleRequirements = async () => {
  try {
    styleSaving.value = true
    await ensureProjectId()
    await projectApi.updateStyleRequirements(projectId.value, {
      author_voice_keywords: styleForm.author_voice_keywords,
      avoid_patterns: styleForm.avoid_patterns,
      preferred_rhythm: styleForm.preferred_rhythm,
      narrative_distance: styleForm.narrative_distance,
      dialogue_density: styleForm.dialogue_density
    })
    styleDialogVisible.value = false
    ElMessage.success('风格要求已保存')
  } catch (error) {
    console.error('保存风格要求失败:', error)
  } finally {
    styleSaving.value = false
  }
}

const extractStyleRequirements = async () => {
  try {
    styleLoading.value = true
    await ensureProjectId()
    const payload = await projectApi.extractStyleRequirements(projectId.value, { sample_chapter_count: 3 })
    const req = payload?.style_requirements || {}
    styleForm.author_voice_keywords = req.author_voice_keywords || []
    styleForm.avoid_patterns = req.avoid_patterns || []
    styleForm.preferred_rhythm = req.preferred_rhythm || ''
    styleForm.narrative_distance = req.narrative_distance || ''
    styleForm.dialogue_density = req.dialogue_density || ''
    ElMessage.success('已从最近样章提取风格要求')
  } catch (error) {
    console.error('提取风格要求失败:', error)
  } finally {
    styleLoading.value = false
  }
}

const deleteRecentChapter = async (chapter) => {
  if (!chapter?.id) return
  try {
    await ElMessageBox.confirm(
      `确认删除“第${chapter.number}章 ${chapter.title || ''}”？删除后无法恢复。`,
      '删除章节',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )
    deletingChapterId.value = chapter.id
    await novelApi.deleteChapter(route.params.id, chapter.id)
    await loadRecentChapters()
    ElMessage.success('章节已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除章节失败:', error)
    }
  } finally {
    deletingChapterId.value = ''
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
  await loadStyleRequirements()
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

.chapter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.branch-toolbar-left {
  display: flex;
  gap: 8px;
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

.draft-compare {
  margin-top: 12px;
}

.compare-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.compare-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.compare-body {
  white-space: pre-wrap;
  line-height: 1.7;
  max-height: 220px;
  overflow-y: auto;
}

.risk-notes {
  margin-top: 10px;
}
</style>
