<template>
  <section class="inline-result-block" :class="[`inline-result-${resultType}`]">
    <div class="inline-result-top">
      <div>
        <div class="inline-result-tag">{{ resultLabel }}</div>
        <h4>{{ title }}</h4>
      </div>
      <div v-if="hint" class="inline-result-hint">{{ hint }}</div>
    </div>

    <p v-if="description" class="inline-result-description">{{ description }}</p>

    <template v-if="resultType === 'candidate'">
      <div class="candidate-block">
        <div class="candidate-label">候选内容</div>
        <pre class="candidate-content">{{ resultText || '暂无候选内容' }}</pre>
      </div>
    </template>

    <template v-else-if="resultType === 'diff'">
      <div class="diff-grid">
        <div class="diff-column">
          <div class="diff-label before">原正文</div>
          <div class="diff-stack">
            <div
              v-for="(item, index) in diffRows"
              :key="`before-${index}`"
              class="diff-row"
              :class="rowToneClass(item.tone)"
            >
              <template v-if="item.beforeTokens?.length">
                <span
                  v-for="(token, tokenIndex) in item.beforeTokens"
                  :key="`before-token-${index}-${tokenIndex}`"
                  class="diff-token"
                  :class="tokenToneClass(token.tone)"
                >
                  {{ token.text }}
                </span>
              </template>
              <template v-else>
                {{ item.before || ' ' }}
              </template>
            </div>
          </div>
        </div>
        <div class="diff-column">
          <div class="diff-label after">改写结果</div>
          <div class="diff-stack">
            <div
              v-for="(item, index) in diffRows"
              :key="`after-${index}`"
              class="diff-row"
              :class="rowToneClass(item.tone)"
            >
              <template v-if="item.afterTokens?.length">
                <span
                  v-for="(token, tokenIndex) in item.afterTokens"
                  :key="`after-token-${index}-${tokenIndex}`"
                  class="diff-token"
                  :class="tokenToneClass(token.tone)"
                >
                  {{ token.text }}
                </span>
              </template>
              <template v-else>
                {{ item.after || ' ' }}
              </template>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div class="inline-result-actions">
      <button
        v-for="item in actions"
        :key="item.key"
        type="button"
        class="inline-result-action"
        :class="{ primary: item.primary }"
        @click="$emit('action', item.key)"
      >
        {{ item.label }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  resultType: {
    type: String,
    default: 'candidate'
  },
  resultLabel: {
    type: String,
    default: '候选稿'
  },
  title: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  },
  originalText: {
    type: String,
    default: ''
  },
  resultText: {
    type: String,
    default: ''
  },
  actions: {
    type: Array,
    default: () => []
  }
})

defineEmits(['action'])

const splitParagraphs = (value) => String(value || '')
  .split(/\r?\n/)
  .map((item) => item.trim())
  .filter(Boolean)

const tokenizeDiffText = (value) => {
  const normalized = String(value || '')
  if (!normalized) return []
  const matched = normalized.match(/[\u4E00-\u9FFF]|[A-Za-z0-9_]+|\s+|[^\sA-Za-z0-9_\u4E00-\u9FFF]/g)
  return matched ? matched.filter((item) => item !== '') : []
}

const buildTokenDiff = (beforeText, afterText) => {
  const beforeTokens = tokenizeDiffText(beforeText)
  const afterTokens = tokenizeDiffText(afterText)
  const rows = Array.from({ length: beforeTokens.length + 1 }, () => Array(afterTokens.length + 1).fill(0))

  for (let i = beforeTokens.length - 1; i >= 0; i -= 1) {
    for (let j = afterTokens.length - 1; j >= 0; j -= 1) {
      rows[i][j] = beforeTokens[i] === afterTokens[j]
        ? rows[i + 1][j + 1] + 1
        : Math.max(rows[i + 1][j], rows[i][j + 1])
    }
  }

  const beforeResult = []
  const afterResult = []
  let i = 0
  let j = 0

  while (i < beforeTokens.length && j < afterTokens.length) {
    if (beforeTokens[i] === afterTokens[j]) {
      beforeResult.push({ text: beforeTokens[i], tone: 'same' })
      afterResult.push({ text: afterTokens[j], tone: 'same' })
      i += 1
      j += 1
      continue
    }

    if (rows[i + 1][j] >= rows[i][j + 1]) {
      beforeResult.push({ text: beforeTokens[i], tone: 'removed' })
      i += 1
    } else {
      afterResult.push({ text: afterTokens[j], tone: 'added' })
      j += 1
    }
  }

  while (i < beforeTokens.length) {
    beforeResult.push({ text: beforeTokens[i], tone: 'removed' })
    i += 1
  }

  while (j < afterTokens.length) {
    afterResult.push({ text: afterTokens[j], tone: 'added' })
    j += 1
  }

  return { beforeTokens: beforeResult, afterTokens: afterResult }
}

const diffRows = computed(() => {
  const beforeList = splitParagraphs(props.originalText)
  const afterList = splitParagraphs(props.resultText)
  const total = Math.max(beforeList.length, afterList.length)
  const rows = []

  for (let index = 0; index < total; index += 1) {
    const before = beforeList[index] || ''
    const after = afterList[index] || ''
    let tone = 'same'

    if (before && !after) tone = 'removed'
    else if (!before && after) tone = 'added'
    else if (before !== after) tone = 'changed'

    const tokenDiff = tone === 'changed'
      ? buildTokenDiff(before, after)
      : {
          beforeTokens: before ? [{ text: before, tone: 'same' }] : [],
          afterTokens: after ? [{ text: after, tone: 'same' }] : []
        }

    rows.push({
      before,
      after,
      tone,
      beforeTokens: tokenDiff.beforeTokens,
      afterTokens: tokenDiff.afterTokens
    })
  }

  return rows.length ? rows : [{ before: '', after: '', tone: 'same' }]
})

const rowToneClass = (tone) => ({
  same: 'tone-same',
  changed: 'tone-changed',
  added: 'tone-added',
  removed: 'tone-removed'
}[tone] || 'tone-same')

const tokenToneClass = (tone) => ({
  same: 'token-same',
  added: 'token-added',
  removed: 'token-removed'
}[tone] || 'token-same')
</script>

<style scoped>
.inline-result-block {
  width: 100%;
  max-width: 920px;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.inline-result-candidate {
  border-color: #BFDBFE;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
}

.inline-result-diff {
  border-color: #D1FAE5;
  background: linear-gradient(180deg, #FFFFFF 0%, #F7FFFB 100%);
}

.inline-result-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.inline-result-tag {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #6B7280;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.inline-result-top h4 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.inline-result-hint {
  font-size: 12px;
  color: #6B7280;
}

.inline-result-description {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #4B5563;
}

.candidate-block {
  margin-top: 14px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid #DBEAFE;
  background: #F8FBFF;
}

.candidate-label,
.diff-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #374151;
}

.candidate-content {
  margin: 0;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
  color: #1F2937;
}

.diff-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.diff-column {
  min-width: 0;
}

.diff-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.diff-row {
  min-height: 46px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #E5E7EB;
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: 13px;
  color: #1F2937;
}

.diff-token {
  white-space: pre-wrap;
}

.token-added {
  background: rgba(34, 197, 94, 0.16);
  border-radius: 4px;
}

.token-removed {
  background: rgba(239, 68, 68, 0.16);
  border-radius: 4px;
  text-decoration: line-through;
}

.tone-same {
  background: #F9FAFB;
}

.tone-changed {
  background: #FFFBEB;
  border-color: #FDE68A;
}

.tone-added {
  background: #F0FDF4;
  border-color: #BBF7D0;
}

.tone-removed {
  background: #FEF2F2;
  border-color: #FECACA;
}

.inline-result-actions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.inline-result-action {
  border: 1px solid #D1D5DB;
  background: #FFFFFF;
  color: #374151;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
}

.inline-result-action.primary {
  border-color: #2563EB;
  background: #2563EB;
  color: #FFFFFF;
}

@media (max-width: 960px) {
  .diff-grid {
    grid-template-columns: 1fr;
  }
}
</style>
