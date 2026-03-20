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
                placeholder="请描述续写的剧情方向，如：主角突破筑基期，遇到新的敌人..."
              />
            </el-form-item>
            <el-form-item label="剧情分支">
              <div class="branch-panel">
                <el-button :loading="branchLoading" @click="generateBranches">生成分支</el-button>
                <el-radio-group v-model="selectedBranchId" class="branch-radio-group">
                  <el-radio v-for="item in branches" :key="item.id" :label="item.id">
                    {{ item.title }}：{{ item.summary }}
                  </el-radio>
                </el-radio-group>
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
              <span class="switch-tip">开启后将模仿原文风格</span>
            </el-form-item>

            <el-form-item label="连贯性检查">
              <el-switch v-model="form.enable_consistency_check" />
              <span class="switch-tip">开启后将检查人物状态、时间线一致性</span>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="generating" @click="generateChapter">
                <el-icon><Edit /></el-icon>
                延展剧情
              </el-button>
              <el-button type="success" :loading="generatingNext" @click="continueNextChapter">
                <el-icon><Edit /></el-icon>
                继续生成
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-if="generatedContent" class="result-card">
          <template #header>
            <div class="card-header">
              <span>生成结果</span>
              <el-button size="small" @click="copyContent">
                <el-icon><CopyDocument /></el-icon>
                复制
              </el-button>
            </div>
          </template>

          <div class="content-info">
            <el-tag>字数：{{ generatedContent.word_count }}</el-tag>
            <el-tag v-if="generatedContent.consistency_report?.is_valid" type="success">连贯性检查通过</el-tag>
            <el-tag v-else-if="generatedContent.consistency_report" type="danger">连贯性检查未通过</el-tag>
          </div>

          <el-divider />

          <div class="content-body">
            {{ generatedContent.content }}
          </div>

          <el-divider />

          <div class="content-actions">
            <el-button type="primary" disabled>{{ saveHintLabel }}</el-button>
            <el-button @click="regenerate">重新生成</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="tips-card">
          <template #header>
            <span>续写提示</span>
          </template>

          <el-collapse>
            <el-collapse-item title="如何描述剧情方向？" name="1">
              <p>描述要生成的剧情走向，例如：</p>
              <ul>
                <li>主角突破境界</li>
                <li>遇到新的敌人</li>
                <li>获得新的功法</li>
                <li>人物关系发展</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="如何提高生成质量？" name="2">
              <ul>
                <li>先进行文风分析</li>
                <li>先进行剧情分析</li>
                <li>开启文风模仿</li>
                <li>开启连贯性检查</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="关于连贯性检查" name="3">
              <p>系统会自动检查：</p>
              <ul>
                <li>人物修为状态</li>
                <li>时间线一致性</li>
                <li>伏笔回收情况</li>
              </ul>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <span>最近章节</span>
          </template>

          <el-scrollbar height="200px">
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
import { novelApi, writingApi } from '@/api'

const route = useRoute()
const generating = ref(false)
const generatingNext = ref(false)
const branchLoading = ref(false)
const generatedContent = ref(null)
const recentChapters = ref([])
const continueHint = ref('')
const branches = ref([])
const selectedBranchId = ref('')

const form = reactive({
  plot_direction: '',
  chapter_count: 1,
  target_word_count: 2100,
  enable_style_mimicry: true,
  enable_consistency_check: true
})

const selectedBranch = () => branches.value.find((item) => item.id === selectedBranchId.value)

const isPersistedResult = computed(() => {
  const routeName = generatedContent.value?.metadata?.route
  return routeName === 'continue_tool' || routeName === 'first_chapter'
})

const saveHintLabel = computed(() => (isPersistedResult.value ? '已保存到章节列表' : '仅预览，尚未保存'))

const resolveDirection = () => {
  const branch = selectedBranch()
  if (branch) {
    return `${branch.title}：${branch.key_event || ''}。${branch.summary}`
  }
  return form.plot_direction
}

const generateBranches = async () => {
  try {
    branchLoading.value = true
    const result = await writingApi.branches({
      novel_id: route.params.id,
      branch_count: 4,
      direction_hint: form.plot_direction || ''
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

const generateChapter = async () => {
  const direction = resolveDirection()
  if (!direction) {
    ElMessage.warning('请先生成并选择剧情分支，或手动填写剧情方向')
    return
  }

  try {
    generating.value = true
    ElMessage.info('正在延展剧情...')
    generatedContent.value = await writingApi.generate({
      novel_id: route.params.id,
      goal: direction,
      target_word_count: form.target_word_count,
      options: {
        enable_style_mimicry: form.enable_style_mimicry,
        enable_consistency_check: form.enable_consistency_check
      }
    })
    ElMessage.info('Preview only, not saved yet')
    ElMessage.success('创作完成')
  } catch (error) {
    console.error('生成失败:', error)
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
    ElMessage.info('正在延展剧情...')
    generatedContent.value = await writingApi.continue({
      novel_id: route.params.id,
      goal: direction,
      target_word_count: form.target_word_count
    })
    ElMessage.info('Saved to chapter list')
    ElMessage.success('创作完成')
    await loadRecentChapters()
  } catch (error) {
    console.error('续写失败:', error)
  } finally {
    generatingNext.value = false
  }
}

const copyContent = () => {
  if (generatedContent.value?.content) {
    navigator.clipboard.writeText(generatedContent.value.content)
    ElMessage.success('已复制到剪贴板')
  }
}

const regenerate = () => {
  generatedContent.value = null
  generateChapter()
}

const loadRecentChapters = async () => {
  try {
    const novel = await novelApi.get(route.params.id)
    recentChapters.value = novel.chapters?.slice(-5).reverse() || []
    if (!form.plot_direction) {
      const nextChapterNumber = (novel.chapter_count || 0) + 1
      form.plot_direction = route.query.default_goal || `第${nextChapterNumber}章：承接上一章推进主线`
    }
  } catch (error) {
    console.error('加载章节失败:', error)
  }
}

onMounted(() => {
  if (route.query.auto_continue === '1') {
    continueHint.value = '已生成第一章，是否继续创作第二章？'
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
        sessionStorage.removeItem('inktrace_continue_hint')
      }
    } catch (error) {
      sessionStorage.removeItem('inktrace_continue_hint')
    }
  }
  loadRecentChapters()
  generateBranches()
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

.content-info {
  display: flex;
  gap: 10px;
}

.content-body {
  white-space: pre-wrap;
  line-height: 1.8;
  max-height: 400px;
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
  gap: 10px;
}

.branch-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
