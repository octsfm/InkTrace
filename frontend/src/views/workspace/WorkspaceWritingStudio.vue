<template>
  <div class="workspace-writing-studio">
    <!-- Top Bar -->
    <header class="writing-header">
      <div class="title-area">
        <input
          class="chapter-title-input"
          v-model="editorState.chapter.title"
          type="text"
          placeholder="无标题章节"
          @input="workspace.state.markEditorDirty()"
        />
        <div class="status-indicator">
          <span v-if="editorState.saving" class="status-saving">正在保存...</span>
          <span v-else-if="editorState.dirty" class="status-dirty">未保存</span>
          <span v-else class="status-saved">已保存</span>
        </div>
      </div>
      <div class="actions-area">
        <el-button type="primary" :loading="editorState.saving" @click="saveChapter">保存</el-button>
        <!-- Zen mode toggle -->
        <el-button @click="toggleZenMode" :type="workspaceStore.isZenMode ? 'primary' : 'default'" plain>
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </div>
    </header>

    <!-- Main Editor Area -->
    <div class="editor-container" v-loading="editorState.loading">
      <el-empty
        v-if="!editorState.chapter.id && !editorState.loading"
        description="请从左侧目录打开一个章节，或创建新章节。"
      />
      <template v-else>
        <!-- The actual TipTap editor -->
        <editor-content :editor="editor" class="editor-surface" />
      </template>
    </div>

    <!-- Bottom Status Bar -->
    <footer class="writing-footer">
      <div class="footer-left">
        <span class="word-count">{{ wordCount }} 字</span>
      </div>
      <div class="footer-right">
        <!-- Optional AI tools triggers directly in footer or via slash commands -->
        <el-button size="small" text @click="runAiAction('continue')" :loading="editorState.aiRunning">AI 续写</el-button>
        <el-button size="small" text @click="runAiAction('analyze')" :loading="editorState.aiRunning">AI 审查</el-button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { FullScreen } from '@element-plus/icons-vue'

import { useWorkspaceContext } from '@/composables/useWorkspaceContext'
import { useWorkspaceStore } from '@/stores/workspace'

const route = useRoute()
const workspace = useWorkspaceContext()
const workspaceStore = useWorkspaceStore()
const editorState = workspace.state.editor

const selectedChapterId = computed(() => String(route.query.chapterId || workspace.currentChapterId.value || ''))

const wordCount = computed(() => (editorState.chapter.content || '').replace(/\s+/g, '').length)

const editor = useEditor({
  extensions: [
    StarterKit,
    Placeholder.configure({
      placeholder: '按 "/" 呼出 AI 命令，或直接开始写作...'
    })
  ],
  content: '',
  editorProps: {
    attributes: {
      class: 'tiptap-editor'
    }
  },
  onUpdate: ({ editor: nextEditor }) => {
    const nextContent = normalizeEditorText(nextEditor.getText({ blockSeparator: '\n' }))
    if (nextContent !== editorState.chapter.content) {
      editorState.chapter.content = nextContent
      workspace.state.markEditorDirty()
    }
  }
})

const syncEditorFromStore = (content = '') => {
  if (!editor.value) return
  const currentContent = normalizeEditorText(editor.value.getText({ blockSeparator: '\n' }))
  const nextContent = normalizeEditorText(content)
  if (currentContent === nextContent) return

  editor.value.commands.setContent(plainTextToHtml(nextContent), false)
}

const saveChapter = async () => {
  await workspace.saveEditorChapter()
  ElMessage.success('章节已保存')
}

const runAiAction = async (action) => {
  await workspace.runEditorAiAction(action)
  ElMessage.success('AI 任务已提交')
}

const toggleZenMode = () => {
  workspaceStore.isZenMode = !workspaceStore.isZenMode
}

// Helpers
const escapeHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;')

const plainTextToHtml = (value) => {
  const lines = String(value || '').split(/\r?\n/)
  if (!lines.length) return '<p></p>'
  return lines.map((line) => `<p>${line ? escapeHtml(line) : '<br>'}</p>`).join('')
}

const normalizeEditorText = (value) => String(value || '').replace(/\u00a0/g, ' ').trimEnd()

// Watchers
watch(
  () => [selectedChapterId.value, workspace.state.projectId],
  ([chapterId]) => {
    void workspace.loadEditorChapter(chapterId)
  },
  { immediate: true }
)

watch(
  () => [editor.value, editorState.chapter.id, editorState.chapter.content],
  ([nextEditor, , content]) => {
    if (!nextEditor) return
    syncEditorFromStore(content)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style scoped>
.workspace-writing-studio {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #ffffff;
}

.writing-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  border-bottom: 1px solid #F3F4F6;
}

.title-area {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.chapter-title-input {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  border: none;
  outline: none;
  background: transparent;
  width: 50%;
  min-width: 200px;
}

.chapter-title-input::placeholder {
  color: #9CA3AF;
}

.status-indicator {
  font-size: 12px;
}

.status-saving { color: #3B82F6; }
.status-dirty { color: #F59E0B; }
.status-saved { color: #10B981; }

.actions-area {
  display: flex;
  gap: 12px;
}

.editor-container {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  display: flex;
  justify-content: center;
}

.editor-surface {
  width: 100%;
  max-width: 800px; /* Optimal reading/writing width */
  min-height: 100%;
}

.editor-surface :deep(.tiptap-editor) {
  outline: none;
  font-size: 18px;
  line-height: 1.8;
  color: #374151;
  font-family: "LXGW WenKai", "Noto Serif SC", serif;
}

.editor-surface :deep(.tiptap-editor p) {
  margin-bottom: 1.2em;
}

.editor-surface :deep(.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  height: 0;
  color: #9CA3AF;
  pointer-events: none;
}

.writing-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 32px;
  border-top: 1px solid #F3F4F6;
  font-size: 13px;
  color: #6B7280;
}

.footer-left, .footer-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
</style>
