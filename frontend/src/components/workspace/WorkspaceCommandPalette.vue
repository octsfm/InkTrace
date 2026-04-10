<template>
  <div v-if="visible" class="command-palette-overlay" @click.self="$emit('close')">
    <div class="command-palette">
      <div class="palette-header">
        <input
          ref="inputRef"
          :value="query"
          type="text"
          class="palette-input"
          placeholder="搜索视图、章节、剧情弧或任务..."
          @input="$emit('update:query', $event.target.value)"
          @keydown.down.prevent="moveSelection(1)"
          @keydown.up.prevent="moveSelection(-1)"
          @keydown.enter.prevent="confirmSelection"
          @keydown.esc.prevent="$emit('close')"
        />
        <div class="palette-shortcuts">`Ctrl/Cmd+K` 打开，`↑/↓` 选择，`Enter` 执行，`Esc` 关闭</div>
      </div>

      <div class="palette-body">
        <div v-if="props.groupedItems.length" class="palette-groups">
          <section v-for="group in props.groupedItems" :key="group.group" class="palette-group">
            <div class="group-title">{{ group.group }}</div>
            <button
              v-for="(item, index) in group.items"
              :key="item.id"
              type="button"
              class="palette-item"
              :class="{ active: flatItems[selectedIndex]?.id === item.id }"
              @mouseenter="selectedIndex = flatItems.findIndex((entry) => entry.id === item.id)"
              @click="$emit('execute', item)"
            >
              <div class="item-main">
                <span class="item-title">{{ item.title }}</span>
                <span v-if="item.subtitle" class="item-subtitle">{{ item.subtitle }}</span>
              </div>
              <span v-if="item.hint" class="item-hint">{{ item.hint }}</span>
            </button>
          </section>
        </div>

        <div v-else class="palette-empty">
          没有匹配的命令，可以换个关键词试试。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  query: {
    type: String,
    default: ''
  },
  groupedItems: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'execute', 'update:query'])

const inputRef = ref(null)
const selectedIndex = ref(0)

const flatItems = computed(() => (
  (Array.isArray(props.groupedItems) ? props.groupedItems : []).flatMap((group) => (
    Array.isArray(group?.items) ? group.items : []
  ))
))

const moveSelection = (offset) => {
  if (!flatItems.value.length) return
  const next = selectedIndex.value + offset
  if (next < 0) {
    selectedIndex.value = flatItems.value.length - 1
    return
  }
  if (next >= flatItems.value.length) {
    selectedIndex.value = 0
    return
  }
  selectedIndex.value = next
}

const confirmSelection = () => {
  const target = flatItems.value[selectedIndex.value]
  if (!target) return
  emit('execute', target)
}

const scrollActiveItemIntoView = async () => {
  await nextTick()
  const activeItem = document.querySelector('.command-palette .palette-item.active')
  activeItem?.scrollIntoView?.({ block: 'nearest' })
}

watch(
  () => [props.visible, props.query, flatItems.value.length],
  async ([visible]) => {
    selectedIndex.value = 0
    if (!visible) return
    await nextTick()
    inputRef.value?.focus?.()
    void scrollActiveItemIntoView()
  }
)

watch(
  () => selectedIndex.value,
  () => {
    void scrollActiveItemIntoView()
  }
)
</script>

<style scoped>
.command-palette-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  background-color: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 84px 24px 24px;
}

.command-palette {
  width: min(760px, 100%);
  max-height: min(72vh, 760px);
  display: flex;
  flex-direction: column;
  border-radius: 24px;
  overflow: hidden;
  border: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  box-shadow: 0 32px 80px rgba(15, 23, 42, 0.22);
}

.palette-header {
  padding: 16px;
  border-bottom: 1px solid #E5E7EB;
}

.palette-shortcuts {
  margin-top: 10px;
  font-size: 11px;
  color: #9CA3AF;
}

.palette-input {
  width: 100%;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  padding: 14px 16px;
  font-size: 15px;
  color: #111827;
  background-color: #F9FAFB;
  outline: none;
}

.palette-input:focus {
  border-color: #C7D2FE;
  background-color: #FFFFFF;
}

.palette-body {
  overflow-y: auto;
  padding: 12px;
}

.palette-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.palette-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-title {
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #9CA3AF;
}

.palette-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  background-color: #FFFFFF;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
}

.palette-item:hover,
.palette-item.active {
  border-color: #C7D2FE;
  background-color: #F8FAFF;
}

.item-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.item-subtitle {
  font-size: 12px;
  line-height: 1.5;
  color: #6B7280;
}

.item-hint {
  flex-shrink: 0;
  font-size: 11px;
  color: #9CA3AF;
}

.palette-empty {
  padding: 24px;
  text-align: center;
  color: #9CA3AF;
  font-size: 13px;
}
</style>
