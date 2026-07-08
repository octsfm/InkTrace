<template>
  <div class="main-layout" :class="themeClass">
    <header class="header">
      <div class="header-shell">
        <div class="header-left">
          <div class="brand-mark">
            <el-icon class="logo-icon"><Edit /></el-icon>
          </div>
          <div class="brand-copy">
            <span class="logo-text">InkTrace</span>
            <span class="logo-subtitle">Novel Workspace</span>
          </div>
        </div>

        <nav class="header-nav">
          <button
            type="button"
            class="nav-link"
            :class="{ active: $route.path === '/works' }"
            @click="$router.push('/works')"
          >
            书架</button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: $route.path === '/settings' }"
            @click="$router.push('/settings')"
          >
            设置</button>
        </nav>

        <div class="header-right">
          <el-button class="ink-el-button ink-el-button--primary header-back-btn" type="primary" @click="$router.push('/works')">
            返回书架</el-button>
        </div>
      </div>
    </header>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { Edit } from '@element-plus/icons-vue'
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePreferenceStore } from '@/stores/preference'

const preferenceStore = usePreferenceStore()
const { appTheme } = storeToRefs(preferenceStore)
const themeClass = computed(() => `main-layout--theme-${String(appTheme.value || 'light')}`)
</script>

<style scoped>
.main-layout {
  --layout-bg: var(--ink-bg-app);
  --layout-header-bg: color-mix(in srgb, var(--ink-bg-app) 92%, transparent);
  --layout-header-border: var(--ink-border);
  --layout-nav-bg: var(--ink-surface-1);
  --layout-nav-hover-bg: var(--ink-surface-3);
  --layout-nav-text: var(--ink-text-muted);
  --layout-nav-active-text: var(--ink-text-primary);
  --layout-brand-bg: var(--ink-text-primary);
  --layout-brand-icon: var(--ink-surface-1);
  --layout-brand-text: var(--ink-text-primary);
  --layout-brand-subtitle: var(--ink-text-muted);

  height: 100vh;
  overflow: hidden;
  background-color: var(--layout-bg);
}

.main-layout--theme-warm {
  --layout-header-bg: color-mix(in srgb, var(--ink-bg-app) 92%, transparent);
}

.main-layout--theme-dark {
  --layout-header-bg: color-mix(in srgb, var(--ink-bg-app) 94%, transparent);
  --layout-brand-bg: var(--ink-surface-1);
  --layout-brand-icon: var(--ink-text-primary);
}

.header {
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid var(--layout-header-border);
  background-color: var(--layout-header-bg);
  backdrop-filter: blur(12px);
}

.header-shell {
  max-width: 1360px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--layout-brand-bg);
  color: var(--layout-brand-icon);
}

.logo-icon {
  font-size: 20px;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--layout-brand-text);
}

.logo-subtitle {
  font-size: 12px;
  color: var(--layout-brand-subtitle);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border: 1px solid var(--layout-header-border);
  border-radius: 999px;
  background-color: var(--layout-nav-bg);
}

.nav-link {
  border: none;
  background: transparent;
  color: var(--layout-nav-text);
  font-size: 13px;
  font-weight: 500;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: var(--layout-nav-active-text);
  background-color: var(--layout-nav-hover-bg);
}

.nav-link.active {
  color: var(--layout-nav-active-text);
  background-color: var(--layout-nav-hover-bg);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right :deep(.header-back-btn.el-button) {
  min-width: 112px;
}

.main-content {
  height: calc(100vh - 69px);
  overflow-y: auto;
  background-color: var(--layout-bg);
  padding: 0;
}

.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 1100px) {
  .header-shell {
    flex-wrap: wrap;
  }

  .header-nav {
    order: 3;
    width: 100%;
    justify-content: flex-start;
  }
}
</style>

