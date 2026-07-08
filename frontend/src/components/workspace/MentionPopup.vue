<template>
  <div
    v-if="visible"
    class="mention-popup"
    data-test="mention-popup"
    role="listbox"
  >
    <section
      v-if="!groupedSuggestions.length"
      class="mention-popup__empty"
    >
      <p>{{ EMPTY_HINT }}</p>
      <button
        type="button"
        class="mention-popup__create"
        data-test="mention-popup-create-character"
        @click="$emit('create-character', { query })"
      >
        {{ CREATE_CHARACTER_LABEL }}
      </button>
    </section>
    <section
      v-for="group in groupedSuggestions"
      :key="group.type"
      class="mention-popup__group"
    >
      <h4 class="mention-popup__title">{{ group.label }}</h4>
      <button
        v-for="item in group.items"
        :key="item.entity_id"
        type="button"
        class="mention-popup__option"
        :class="{ 'mention-popup__option--active': flatIndexMap[item.entity_id] === activeIndex }"
        :data-test="`mention-popup-option-${item.entity_id}`"
        :aria-selected="flatIndexMap[item.entity_id] === activeIndex"
        @click="$emit('select', item)"
      >
        <strong>{{ item.entity_name }}</strong>
        <span>{{ item.summary_preview }}</span>
      </button>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const EMPTY_HINT = '试试其他关键词，或'
const CREATE_CHARACTER_LABEL = '新建人物'

const typeLabelMap = {
  character: '人物',
  event: '事件',
  foreshadow: '伏笔'
}

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  suggestions: {
    type: Array,
    default: () => []
  },
  query: {
    type: String,
    default: ''
  },
  activeIndex: {
    type: Number,
    default: -1
  }
})

defineEmits(['select', 'create-character'])

const groupedSuggestions = computed(() => {
  const groups = new Map()
  for (const item of props.suggestions) {
    const type = String(item?.entity_type || 'character')
    if (!groups.has(type)) {
      groups.set(type, {
        type,
        label: typeLabelMap[type] || type,
        items: []
      })
    }
    groups.get(type).items.push(item)
  }
  return Array.from(groups.values())
})

const flatIndexMap = computed(() => {
  const entries = {}
  props.suggestions.forEach((item, index) => {
    entries[String(item?.entity_id || index)] = index
  })
  return entries
})
</script>

<style scoped>
.mention-popup {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(320px, 100%);
  border: 1px solid var(--studio-border, var(--ink-border));
  border-radius: 20px;
  background: var(--studio-card-bg, var(--ink-surface-1));
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.14);
  padding: 14px;
}

.mention-popup__group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mention-popup__empty {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--studio-muted, var(--ink-text-secondary));
  font-size: 13px;
}

.mention-popup__empty p {
  margin: 0;
}

.mention-popup__create {
  border: none;
  background: transparent;
  color: var(--ink-primary, var(--ink-accent));
  cursor: pointer;
  padding: 0;
  font-weight: 600;
}

.mention-popup__title {
  margin: 0;
  font-size: 12px;
  color: var(--studio-muted, var(--ink-text-muted));
}

.mention-popup__option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  border: 1px solid var(--studio-border, var(--ink-border));
  border-radius: 14px;
  background: var(--studio-surface, var(--ink-surface-2));
  padding: 10px 12px;
  cursor: pointer;
}

.mention-popup__option strong {
  color: var(--studio-title, var(--ink-text-primary));
}

.mention-popup__option--active {
  border-color: var(--ink-accent, var(--ink-primary));
  background: var(--ink-primary-soft, rgba(79, 124, 255, 0.1));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink-accent, #4f7cff) 28%, transparent);
}

.mention-popup__option span {
  color: var(--studio-muted, var(--ink-text-secondary));
  font-size: 12px;
}
</style>
