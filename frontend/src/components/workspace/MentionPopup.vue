<template>
  <div
    v-if="visible"
    class="mention-popup"
    data-test="mention-popup"
  >
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
        :data-test="`mention-popup-option-${item.entity_id}`"
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

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  suggestions: {
    type: Array,
    default: () => []
  }
})

defineEmits(['select'])

const typeLabelMap = {
  character: '人物',
  event: '事件',
  foreshadow: '伏笔'
}

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
</script>

<style scoped>
.mention-popup {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(320px, 100%);
  border: 1px solid var(--studio-border, #d1d5db);
  border-radius: 20px;
  background: var(--studio-card-bg, #ffffff);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.14);
  padding: 14px;
}

.mention-popup__group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mention-popup__title {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.mention-popup__option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  padding: 10px 12px;
  cursor: pointer;
}

.mention-popup__option strong {
  color: #111827;
}

.mention-popup__option span {
  color: #6b7280;
  font-size: 12px;
}
</style>
