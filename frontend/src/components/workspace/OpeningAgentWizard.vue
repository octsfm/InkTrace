<template>
  <div v-if="visible" class="opening-wizard" data-test="opening-agent-wizard">
    <div class="opening-wizard__backdrop" @click="$emit('close')"></div>
    <div class="opening-wizard__dialog" role="dialog" aria-modal="true" aria-label="开篇助手">
      <header class="opening-wizard__header">
        <div><h4>开篇助手</h4><p>把你的故事想法整理成前三章候选稿，是否采用始终由你决定。</p></div>
        <button type="button" class="ink-button ink-button--ghost" data-test="opening-close" @click="$emit('close')">关闭</button>
      </header>

      <ol class="opening-wizard__steps">
        <li v-for="(item, index) in steps" :key="item" :class="{ active: step === index }">{{ index + 1 }}. {{ item }}</li>
      </ol>

      <section class="opening-wizard__content" data-test="opening-step">
        <template v-if="step === 0">
          <h5>先说说你的故事</h5>
          <p class="note">不用写得完整，一两句话就够。已有大纲和人物设定会自动参考。</p>
          <label>这是一个什么故事？<textarea v-model.trim="form.storyPremise" data-test="opening-story-premise" /></label>
          <label>主角现在最想要什么？<input v-model.trim="form.protagonistDesire" data-test="opening-protagonist-desire" /></label>
          <label>希望读者看完第三章时最期待什么？<input v-model.trim="form.thirdChapterExpectation" data-test="opening-third-chapter-expectation" /></label>
          <details>
            <summary>添加灵感参考（可跳过）</summary>
            <p class="note">请只添加你有权使用的内容。系统不会把参考原文加入你的小说，也不会长期保存原文。</p>
            <button v-if="references.length < 3" type="button" class="ink-button ink-button--ghost" data-test="opening-add-reference" @click="addReference">添加一部参考</button>
            <div v-for="(reference, index) in references" :key="reference.localId" class="reference-card">
              <label>作品名称<input v-model.trim="reference.title" :data-test="`opening-reference-title-${index}`" /></label>
              <label>前 1–3 章文本<textarea v-model="reference.text" :data-test="`opening-reference-text-${index}`" /></label>
              <div class="reference-meta"><span>{{ reference.text.length }} / 30,000 字</span><button type="button" class="ink-button ink-button--ghost" @click="removeReference(index)">移除</button></div>
            </div>
            <label v-if="references.length" class="checkbox"><input v-model="rightsConfirmed" type="checkbox" data-test="opening-rights-confirm" />我确认有权将这些内容用于个人创作分析</label>
          </details>
        </template>

        <template v-else-if="step === 1">
          <h5>选择一个开篇方向</h5>
          <p class="note">这里只是在定开篇思路，还不会修改你的章节。</p>
          <div v-if="!directions.length" class="empty">正在整理三个开篇方向…</div>
          <button v-for="item in directions" :key="item.direction_id" type="button" class="direction-card"
            :class="{ selected: selectedId === item.direction_id }" :data-test="`opening-direction-${item.direction_id}`"
            @click="selectedId = item.direction_id">
            <strong>{{ item.name }}</strong><span>{{ item.summary }}</span>
            <small>{{ (item.chapter_goals || []).join(' → ') }}</small>
          </button>
          <div class="direction-actions">
            <button type="button" class="ink-button ink-button--ghost" data-test="opening-edit-direction" :disabled="!selectedId || busy" @click="startEditing(false)">改一改这个方向</button>
            <button type="button" class="ink-button ink-button--ghost" data-test="opening-write-direction" :disabled="!directions.length || busy" @click="startEditing(true)">我自己写方向</button>
            <button type="button" class="ink-button ink-button--ghost" data-test="opening-new-batch" :disabled="busy" @click="emit('refresh-directions')">这批不合适，换一批</button>
          </div>
          <div v-if="editingDirection" class="direction-editor">
            <h6>{{ writingOwnDirection ? '写下你的开篇方向' : '把这个方向改成你想要的样子' }}</h6>
            <label>方向名称<input v-model.trim="directionForm.name" data-test="opening-direction-name-input" /></label>
            <label>开篇思路<textarea v-model.trim="directionForm.summary" data-test="opening-direction-summary-input" /></label>
            <label v-for="(_, index) in directionForm.chapterGoals" :key="index">
              第 {{ index + 1 }} 章要发生什么？
              <input v-model.trim="directionForm.chapterGoals[index]" :data-test="`opening-direction-goal-${index}`" />
            </label>
            <div class="direction-actions">
              <button type="button" class="ink-button ink-button--ghost" @click="editingDirection = false">取消</button>
              <button type="button" class="ink-button ink-button--primary" data-test="opening-save-direction" :disabled="!directionFormReady || busy" @click="saveDirection">保存为新方向</button>
            </div>
          </div>
        </template>

        <template v-else-if="step === 2">
          <h5>生成前三章候选稿</h5>
          <p>接下来只会生成候选稿，不会创建或覆盖正式章节。你可以逐章修改、采用或丢弃。</p>
          <div class="summary-card"><strong>{{ selectedDirection?.name }}</strong><span>{{ selectedDirection?.summary }}</span></div>
        </template>

        <template v-else>
          <h5>候选稿已经准备好</h5>
          <p>请到候选稿区逐章阅读和决定。不会一次性应用三章。</p>
          <ul><li v-for="item in chapterResults" :key="item.chapter_no">第 {{ item.chapter_no }} 章：{{ chapterStatus(item.status) }}</li></ul>
        </template>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      </section>

      <footer class="opening-wizard__footer">
        <button type="button" class="ink-button ink-button--ghost" :disabled="step === 0 || busy" @click="step -= 1">上一步</button>
        <button v-if="step === 0" type="button" class="ink-button ink-button--primary" data-test="opening-create-directions" :disabled="!briefReady || busy" @click="submitBrief">看看开篇方向</button>
        <button v-else-if="step === 1" type="button" class="ink-button ink-button--primary" data-test="opening-confirm-direction" :disabled="!selectedId || busy" @click="confirmSelected">就选这个</button>
        <button v-else-if="step === 2" type="button" class="ink-button ink-button--primary" data-test="opening-generate" :disabled="busy" @click="generateDrafts">生成前三章候选稿</button>
        <button v-else type="button" class="ink-button ink-button--primary" data-test="opening-finish" @click="$emit('close')">去看候选稿</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  directions: { type: Array, default: () => [] },
  selectedDirection: { type: Object, default: null },
  draftBatch: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  analysis: { type: Object, default: () => ({}) },
  strategy: { type: Object, default: () => ({}) },
  riskLevel: { type: String, default: 'low' }
})
const emit = defineEmits(['close', 'create-directions', 'refresh-directions', 'revise-direction', 'confirm-direction', 'generate-drafts'])
const steps = ['说说故事', '选择方向', '生成候选稿', '逐章决定']
const step = ref(0)
const selectedId = ref('')
const rightsConfirmed = ref(false)
const references = ref([])
const editingDirection = ref(false)
const writingOwnDirection = ref(false)
const form = reactive({ storyPremise: '', protagonistDesire: '', thirdChapterExpectation: '' })
const directionForm = reactive({ name: '', summary: '', chapterGoals: ['', '', ''], advantages: [], risks: [] })
const referencesReady = computed(() => !references.value.length || (
  rightsConfirmed.value && references.value.every((item) => item.title && item.text && item.text.length <= 30000)
))
const briefReady = computed(() => form.storyPremise && form.protagonistDesire && form.thirdChapterExpectation && referencesReady.value)
const chapterResults = computed(() => props.draftBatch?.chapter_results || [])
const directionFormReady = computed(() => directionForm.name && directionForm.summary && directionForm.chapterGoals.every(Boolean))

const addReference = () => { if (references.value.length < 3) references.value.push({ localId: Date.now() + Math.random(), title: '', text: '' }) }
const removeReference = (index) => { references.value.splice(index, 1); if (!references.value.length) rightsConfirmed.value = false }
const submitBrief = () => emit('create-directions', {
  ...form,
  rightsConfirmed: rightsConfirmed.value,
  references: references.value.map((item) => ({ title: item.title, chaptersText: [item.text] }))
})
const confirmSelected = () => emit('confirm-direction', selectedId.value)
const startEditing = (writeOwn) => {
  const source = props.directions.find((item) => item.direction_id === selectedId.value) || props.directions[0]
  if (!source) return
  selectedId.value = source.direction_id
  writingOwnDirection.value = writeOwn
  directionForm.name = writeOwn ? '' : source.name || ''
  directionForm.summary = writeOwn ? '' : source.summary || ''
  directionForm.chapterGoals = writeOwn ? ['', '', ''] : [...(source.chapter_goals || []).slice(0, 3)]
  while (directionForm.chapterGoals.length < 3) directionForm.chapterGoals.push('')
  directionForm.advantages = writeOwn ? [] : [...(source.advantages || [])]
  directionForm.risks = writeOwn ? [] : [...(source.risks || [])]
  editingDirection.value = true
}
const saveDirection = () => {
  emit('revise-direction', {
    directionId: selectedId.value, name: directionForm.name, summary: directionForm.summary,
    chapterGoals: [...directionForm.chapterGoals], advantages: [...directionForm.advantages], risks: [...directionForm.risks]
  })
  editingDirection.value = false
}
const generateDrafts = () => emit('generate-drafts')
const chapterStatus = (value) => value === 'waiting_review' ? '等你查看' : value === 'failed' ? '生成失败，可以重试' : '已保留'

watch(() => props.directions, (value) => { if (value.length && step.value === 0) step.value = 1 }, { deep: true, immediate: true })
watch(() => props.selectedDirection, (value) => { if (value?.direction_id) { selectedId.value = value.direction_id; step.value = 2 } })
watch(() => props.draftBatch, (value) => { if (value?.draft_batch_id) step.value = 3 })
watch(() => props.visible, (visible) => { if (visible && !props.draftBatch) step.value = props.selectedDirection ? 2 : props.directions.length ? 1 : 0 })
</script>

<style scoped>
.opening-wizard { position: fixed; inset: 0; z-index: 60; }
.opening-wizard__backdrop { position: absolute; inset: 0; background: rgba(15, 23, 42, .48); }
.opening-wizard__dialog { position: relative; width: min(720px, calc(100vw - 32px)); max-height: calc(100vh - 48px); overflow: auto; margin: 24px auto; padding: 20px; border-radius: 16px; background: var(--ink-surface, #fff); box-shadow: 0 24px 64px rgba(15, 23, 42, .22); }
.opening-wizard__header, .opening-wizard__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.opening-wizard__header h4 { margin: 0 0 4px; font-size: 20px; }
.opening-wizard__header p, .note { margin: 0; color: #64748b; font-size: 13px; }
.opening-wizard__steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 20px 0; padding: 0; list-style: none; font-size: 12px; color: #94a3b8; }
.opening-wizard__steps li { padding: 8px; border-radius: 8px; background: #f1f5f9; text-align: center; }
.opening-wizard__steps li.active { color: #2563eb; background: #eff6ff; font-weight: 700; }
.opening-wizard__content { display: grid; gap: 14px; min-height: 280px; }
.opening-wizard__content label { display: grid; gap: 6px; font-size: 13px; font-weight: 600; }
textarea, input { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; padding: 9px 10px; font: inherit; }
textarea { min-height: 80px; resize: vertical; }
.checkbox { grid-template-columns: auto 1fr !important; align-items: center; font-weight: 400 !important; }
.checkbox input { width: auto; }
.reference-card { display: grid; gap: 10px; margin-top: 10px; padding: 12px; border: 1px solid #dbe3ee; border-radius: 10px; }
.reference-meta { display: flex; align-items: center; justify-content: space-between; color: #64748b; font-size: 12px; }
.direction-card, .summary-card { display: grid; gap: 6px; width: 100%; padding: 14px; border: 1px solid #dbe3ee; border-radius: 12px; background: #fff; text-align: left; }
.direction-card.selected { border-color: #2563eb; background: #eff6ff; }
.direction-card span, .direction-card small, .summary-card span { color: #64748b; }
.direction-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.direction-editor { display: grid; gap: 10px; padding: 14px; border: 1px solid #bfdbfe; border-radius: 12px; background: #eff6ff; }
.direction-editor h6 { margin: 0; font-size: 15px; }
.opening-wizard__footer { margin-top: 20px; }
.error { color: #dc2626; }
</style>
