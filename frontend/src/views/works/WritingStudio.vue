<template>
  <main class="writing-studio-shell" data-testid="writing-studio-shell">
    <header class="studio-header" data-region="Header">
      <div>
        <p class="eyebrow">Workbench</p>
        <h1>WritingStudio Shell</h1>
      </div>
      <span class="work-id">work: {{ workId }}</span>
    </header>

    <section class="studio-layout">
      <aside class="chapter-sidebar" data-region="ChapterSidebar">
        <h2>ChapterSidebar</h2>
        <p>Stage 0 placeholder only.</p>
      </aside>

      <section class="editor-area" data-region="Editor">
        <input class="title-placeholder" type="text" disabled placeholder="Title shell" />
        <textarea class="editor-placeholder" disabled placeholder="PureTextEditor shell"></textarea>
      </section>

      <nav class="asset-rail" data-region="AssetRail" aria-label="AssetRail">
        <button type="button" disabled>Outline</button>
        <button type="button" disabled>Timeline</button>
        <button type="button" disabled>Foreshadow</button>
        <button type="button" disabled>Character</button>
      </nav>

      <aside class="asset-drawer" data-region="AssetDrawer">
        <h2>AssetDrawer</h2>
        <p>Drawer modules are mounted in later stages.</p>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const workId = computed(() => String(route.params.id || ''))
</script>

<style scoped>
.writing-studio-shell {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 100vh;
  background: #f8fafc;
  color: #111827;
}

.studio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.studio-header h1 {
  margin: 0;
  font-size: 22px;
}

.work-id {
  color: #64748b;
  font-size: 13px;
}

.studio-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 64px 360px;
  gap: 12px;
  min-height: 0;
  padding: 12px;
}

.chapter-sidebar,
.editor-area,
.asset-rail,
.asset-drawer {
  border: 1px dashed #cbd5e1;
  border-radius: 18px;
  background: #ffffff;
}

.chapter-sidebar,
.asset-drawer {
  padding: 18px;
}

.chapter-sidebar h2,
.asset-drawer h2 {
  margin: 0;
  font-size: 16px;
}

.chapter-sidebar p,
.asset-drawer p {
  color: #64748b;
  font-size: 13px;
}

.editor-area {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
  padding: 18px;
}

.title-placeholder,
.editor-placeholder {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  color: #64748b;
}

.title-placeholder {
  height: 44px;
  padding: 0 14px;
}

.editor-placeholder {
  min-height: 0;
  resize: none;
  padding: 14px;
}

.asset-rail {
  display: grid;
  align-content: start;
  gap: 8px;
  padding: 8px;
}

.asset-rail button {
  min-height: 44px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
  color: #64748b;
}

@media (max-width: 960px) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
}
</style>
