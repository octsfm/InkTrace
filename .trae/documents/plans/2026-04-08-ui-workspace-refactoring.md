# InkTrace UI Refactoring (Phase A & B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the InkTrace frontend from a multi-page CMS style to a unified, 4-pane "Novel Workspace" IDE, replacing `textarea` with a rich TipTap editor as the core writing studio.

**Architecture:** Create a single `NovelWorkspace.vue` container with a Pinia store (`useWorkspaceStore`) managing the global state (current view, chapter, etc.). Implement `WritingStudio.vue` using TipTap for the main editing area, moving AI interactions into inline/contextual panels rather than separate pages.

**Tech Stack:** Vue 3, Vue Router, Pinia, Element Plus, TipTap (ProseMirror).

---

### Task 1: Setup Dependencies and State Management

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/stores/workspace.js`

- [ ] **Step 1: Install TipTap dependencies**

Run:
```bash
cd frontend && npm install @tiptap/vue-3 @tiptap/starter-kit @tiptap/extension-placeholder
```

- [ ] **Step 2: Create Workspace Pinia Store**

Create `frontend/src/stores/workspace.js`:
```javascript
import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    novelId: null,
    novelInfo: null,
    activeView: 'writing', // 'overview' | 'writing' | 'structure' | 'tasks'
    activeChapterId: null,
    isCopilotOpen: true,
    activeCopilotTab: 'chat',
    isZenMode: false
  }),
  actions: {
    initWorkspace(novelId) {
      this.novelId = novelId
      // Mock data for now, real implementation will fetch from API
      this.novelInfo = { title: 'Loading...' }
    },
    switchView(viewName) {
      this.activeView = viewName
    },
    openChapter(chapterId) {
      this.activeChapterId = chapterId
      this.activeView = 'writing'
      this.isZenMode = false
    }
  }
})
```

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/stores/workspace.js
git commit -m "chore: add tiptap dependencies and workspace store"
```

### Task 2: Configure Workspace Routing and Base Layout

**Files:**
- Modify: `frontend/src/router/index.js`
- Create: `frontend/src/views/Workspace.vue`

- [ ] **Step 1: Add Workspace route**

Modify `frontend/src/router/index.js` to include the new Workspace route:

```javascript
import { createRouter, createWebHistory } from 'vue-router'
// ... existing imports ...

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // ... existing routes ...
    {
      path: '/workspace/:id',
      name: 'Workspace',
      component: () => import('../views/Workspace.vue'),
      props: true
    }
  ]
})
// ...
```

- [ ] **Step 2: Create Base Workspace Layout Component**

Create `frontend/src/views/Workspace.vue`:
```vue
<template>
  <div class="workspace-container" :class="{ 'zen-mode': store.isZenMode }">
    <!-- Left 1: App Navigation -->
    <nav class="app-sidebar" v-show="!store.isZenMode">
      <div class="nav-item" :class="{ active: store.activeView === 'overview' }" @click="store.switchView('overview')">概览</div>
      <div class="nav-item" :class="{ active: store.activeView === 'writing' }" @click="store.switchView('writing')">写作</div>
      <div class="nav-item" :class="{ active: store.activeView === 'structure' }" @click="store.switchView('structure')">结构</div>
    </nav>

    <!-- Left 2: Object Navigation -->
    <aside class="context-sidebar" v-show="!store.isZenMode">
      <div v-if="['writing', 'overview'].includes(store.activeView)">
        <h3>章节目录</h3>
        <div class="chapter-item" @click="store.openChapter('1')">第1章</div>
      </div>
    </aside>

    <!-- Middle: Main Content Area -->
    <main class="main-content">
      <div v-if="store.activeView === 'writing'" style="height: 100%;">
        <!-- Placeholder for WritingStudio -->
        <h2>写作台 (Chapter: {{ store.activeChapterId || '未选择' }})</h2>
      </div>
      <div v-else>
        <h2>{{ store.activeView }}</h2>
      </div>
    </main>

    <!-- Right: Copilot Sidebar -->
    <aside class="copilot-sidebar" v-show="store.isCopilotOpen && !store.isZenMode">
      <h3>AI Copilot</h3>
    </aside>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const store = useWorkspaceStore()

onMounted(() => {
  store.initWorkspace(route.params.id)
})
</script>

<style scoped>
.workspace-container { display: flex; height: 100vh; width: 100vw; overflow: hidden; background-color: #F8FAFC; }
.app-sidebar { width: 64px; background: #fff; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; align-items: center; padding-top: 1rem; }
.nav-item { padding: 10px; cursor: pointer; font-size: 12px; margin-bottom: 10px; }
.nav-item.active { color: #409EFF; font-weight: bold; }
.context-sidebar { width: 240px; background: #fff; border-right: 1px solid #e2e8f0; padding: 1rem; }
.main-content { flex: 1; padding: 2rem; overflow-y: auto; background: #fff; margin: 0 1rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
.copilot-sidebar { width: 300px; background: #F8FAFC; border-left: 1px solid #e2e8f0; padding: 1rem; }
.workspace-container.zen-mode .app-sidebar,
.workspace-container.zen-mode .context-sidebar,
.workspace-container.zen-mode .copilot-sidebar { display: none; }
.workspace-container.zen-mode .main-content { margin: 0 auto; max-width: 800px; box-shadow: none; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.js frontend/src/views/Workspace.vue
git commit -m "feat: add unified Workspace layout and routing"
```

### Task 3: Implement TipTap Writing Studio

**Files:**
- Create: `frontend/src/components/workspace/WritingStudio.vue`
- Modify: `frontend/src/views/Workspace.vue`

- [ ] **Step 1: Create WritingStudio Component with TipTap**

Create `frontend/src/components/workspace/WritingStudio.vue`:
```vue
<template>
  <div class="writing-studio">
    <div v-if="!chapterId" class="empty-state">
      <p>请在左侧选择或创建一个章节以开始写作。</p>
    </div>
    <div v-else class="editor-wrapper">
      <editor-content :editor="editor" class="tiptap-editor" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

const props = defineProps({
  chapterId: { type: String, default: null }
})

const editor = ref(null)

const initEditor = () => {
  if (editor.value) {
    editor.value.destroy()
  }
  editor.value = new Editor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: '在此输入正文，或输入 / 唤出 AI 助手...',
      })
    ],
    content: '<p>这是测试章节 ' + props.chapterId + ' 的内容。</p>',
    editorProps: {
      attributes: { class: 'prose focus:outline-none max-w-none' }
    }
  })
}

watch(() => props.chapterId, (newId) => {
  if (newId) {
    initEditor()
  }
}, { immediate: true })

onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.destroy()
  }
})
</script>

<style>
.writing-studio { height: 100%; display: flex; flex-direction: column; }
.empty-state { display: flex; justify-content: center; align-items: center; height: 100%; color: #94a3b8; }
.editor-wrapper { flex: 1; padding: 2rem; cursor: text; }
.tiptap-editor .ProseMirror { min-height: 500px; outline: none; font-size: 16px; line-height: 1.8; color: #334155; }
.tiptap-editor .ProseMirror p.is-editor-empty:first-child::before {
  content: attr(data-placeholder); float: left; color: #cbd5e1; pointer-events: none; height: 0;
}
</style>
```

- [ ] **Step 2: Integrate WritingStudio into Workspace**

Modify `frontend/src/views/Workspace.vue`:
```vue
<script setup>
// Add this import
import WritingStudio from '../components/workspace/WritingStudio.vue'
// ... existing script code ...
</script>

<template>
  <!-- ... inside main-content ... -->
      <div v-if="store.activeView === 'writing'" style="height: 100%;">
        <WritingStudio :chapter-id="store.activeChapterId" />
      </div>
  <!-- ... rest of template ... -->
</template>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workspace/WritingStudio.vue frontend/src/views/Workspace.vue
git commit -m "feat: integrate TipTap editor into Writing Studio"
```

### Task 4: Integrate Workspace Link to Dashboard

**Files:**
- Modify: `frontend/src/views/NovelList.vue`

- [ ] **Step 1: Modify NovelList to route to Workspace**

Modify `frontend/src/views/NovelList.vue` to point to the new Workspace route when a novel is clicked.
Assuming there's a `<router-link>` or a click handler pushing to `/novel/:id`, change it to `/workspace/:id`.

```javascript
// Locate the navigation logic in frontend/src/views/NovelList.vue
// For example: router.push(`/novel/${row.id}`)
// Change it to: router.push(`/workspace/${row.id}`)
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/NovelList.vue
git commit -m "feat: route from NovelList directly to unified Workspace"
```
