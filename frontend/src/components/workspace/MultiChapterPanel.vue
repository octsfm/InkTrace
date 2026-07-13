<template>
  <div v-if="visible" class="multi-chapter-backdrop" @click.self="$emit('close')">
    <section class="multi-chapter-panel" role="dialog" aria-modal="true" aria-labelledby="multi-chapter-title">
      <header>
        <div>
          <h2 id="multi-chapter-title">准备几章新稿</h2>
          <p>每章写完都会停下来等你。新稿不会自动放进正文。</p>
        </div>
        <button type="button" class="close-button" aria-label="关闭多章续写" @click="$emit('close')">×</button>
      </header>

      <template v-if="!sessionId">
        <fieldset>
          <legend>想先准备几章？</legend>
          <label><input v-model.number="targetChapters" type="radio" :value="3" /> 3 章</label>
          <label><input v-model.number="targetChapters" type="radio" :value="5" /> 5 章</label>
        </fieldset>
        <label class="instruction-field">
          <span>接下来希望故事怎么走？（可以不填）</span>
          <textarea v-model="userInstruction" maxlength="200" placeholder="例如：先推进两人的误会，再让伏笔露出一点线索。" />
        </label>
        <button
          type="button"
          class="ink-button ink-button--primary"
          data-test="multi-chapter-start"
          :disabled="loading || !workId || !chapterId"
          @click="start"
        >
          {{ loading ? '正在准备...' : '开始准备新稿' }}
        </button>
      </template>

      <template v-else>
        <div class="progress-copy" role="status">
          <strong>已准备 {{ progress.completed_count || 0 }} / {{ progress.target_chapters || targetChapters }} 章</strong>
          <span>{{ statusMessage }}</span>
        </div>
        <ol class="chapter-results">
          <li v-for="item in progress.per_chapter || []" :key="item.chapter_index">
            <span>第 {{ item.chapter_index }} 份新稿</span>
            <strong>{{ displayStatus(item.status) }}</strong>
            <button
              v-if="item.candidate_draft_id"
              type="button"
              @click="$emit('open-review')"
            >
              去审阅
            </button>
          </li>
        </ol>
        <div class="panel-actions">
          <button
            v-if="progress.status === 'waiting_user_decision'"
            type="button"
            class="ink-button ink-button--primary"
            @click="advance('continue')"
          >
            继续准备下一章
          </button>
          <button
            v-if="!['completed', 'cancelled', 'failed'].includes(progress.status)"
            type="button"
            class="ink-button ink-button--ghost"
            @click="cancel"
          >
            到这里就好
          </button>
          <button type="button" class="ink-button ink-button--ghost" @click="refresh">刷新状态</button>
        </div>
      </template>

      <p v-if="errorMessage" class="panel-error" role="alert">{{ errorMessage }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { aiApi } from '@/api'

const props = defineProps({
  visible: { type: Boolean, default: false },
  workId: { type: String, default: '' },
  chapterId: { type: String, default: '' }
})
defineEmits(['close', 'open-review'])

const targetChapters = ref(3)
const userInstruction = ref('')
const sessionId = ref('')
const progress = ref({})
const loading = ref(false)
const errorMessage = ref('')
let pollTimer = null

const unwrapData = (payload) => payload?.data ?? payload ?? {}
const buildAction = (prefix) => ({
  caller_type: 'user_action',
  user_action: true,
  idempotency_key: `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
})
const displayStatus = (status) => ({
  pending: '等待开始', running: '正在写', completed: '新稿已准备好',
  blocked: '需要你处理', failed: '没有写完', skipped: '已跳过'
}[status] || '处理中')
const statusMessage = computed(() => ({
  waiting_user_decision: '这一章已经写好，先去审阅，再决定是否继续。',
  running: '正在准备下一章新稿。',
  paused: '已经暂停，写好的新稿仍然保留。',
  completed: '这次的新稿已经全部准备好。',
  cancelled: '这次准备已经结束，写好的新稿仍然保留。',
  failed: '这次没有完成，可以稍后重试。'
}[progress.value.status] || '正在查看进度。'))

const scheduleRefresh = () => {
  clearTimeout(pollTimer)
  if (['running', 'pending'].includes(progress.value.status)) {
    pollTimer = setTimeout(refresh, 2500)
  }
}

const refresh = async () => {
  if (!sessionId.value) return
  try {
    progress.value = unwrapData(await aiApi.getMultiChapterProgress(sessionId.value))
    scheduleRefresh()
  } catch (error) {
    errorMessage.value = error?.userMessage || '暂时没能看到新稿进度。'
  }
}

const start = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = unwrapData(await aiApi.startMultiChapter({
      work_id: props.workId,
      start_chapter_id: props.chapterId,
      target_chapters: targetChapters.value,
      user_instruction: userInstruction.value.trim(),
      caller_type: 'user_action'
    }))
    sessionId.value = String(data.session_id || '')
    progress.value = data
    await refresh()
  } catch (error) {
    errorMessage.value = error?.userMessage || '这次没能开始准备新稿。'
  } finally {
    loading.value = false
  }
}

const advance = async (decision) => {
  try {
    await aiApi.advanceMultiChapter(sessionId.value, { ...buildAction('multi_chapter_advance'), decision })
    await refresh()
  } catch (error) {
    errorMessage.value = error?.userMessage || '暂时不能继续下一章。'
  }
}

const cancel = async () => {
  try {
    await aiApi.cancelMultiChapter(sessionId.value, buildAction('multi_chapter_cancel'))
    await refresh()
  } catch (error) {
    errorMessage.value = error?.userMessage || '暂时没能结束这次准备。'
  }
}

onBeforeUnmount(() => clearTimeout(pollTimer))
</script>

<style scoped>
.multi-chapter-backdrop { position: fixed; inset: 0; z-index: 80; display: flex; justify-content: flex-end; background: rgba(15, 23, 42, 0.28); }
.multi-chapter-panel { width: min(430px, 100vw); height: 100%; overflow-y: auto; padding: 24px; background: var(--ink-surface-1); color: var(--ink-text-primary); box-shadow: var(--ink-shadow-lg); }
.multi-chapter-panel header { display: flex; justify-content: space-between; gap: 18px; }
.multi-chapter-panel h2 { margin: 0; }
.multi-chapter-panel header p, .instruction-field span { color: var(--ink-text-muted); }
.close-button { width: 44px; height: 44px; border: 0; background: transparent; font-size: 24px; cursor: pointer; }
fieldset { display: flex; gap: 24px; margin: 24px 0; padding: 16px; border: 1px solid var(--ink-border); border-radius: var(--ink-radius-md); }
.instruction-field { display: grid; gap: 8px; margin-bottom: 18px; }
.instruction-field textarea { min-height: 110px; resize: vertical; padding: 12px; border: 1px solid var(--ink-border); border-radius: var(--ink-radius-md); }
.progress-copy { display: grid; gap: 6px; margin: 24px 0; }
.chapter-results { display: grid; gap: 10px; padding: 0; list-style: none; }
.chapter-results li { display: grid; grid-template-columns: 1fr auto auto; gap: 12px; align-items: center; padding: 14px; border: 1px solid var(--ink-border); border-radius: var(--ink-radius-md); }
.panel-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
.panel-error { color: var(--ink-danger-text); }
</style>
