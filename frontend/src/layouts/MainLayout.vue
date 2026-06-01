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
          <el-button type="primary" @click="$router.push('/works')">
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
  --layout-bg: #F8FAFC;
  --layout-header-bg: rgba(248, 250, 252, 0.92);
  --layout-header-border: #E5E7EB;
  --layout-nav-bg: #FFFFFF;
  --layout-nav-hover-bg: #F3F4F6;
  --layout-nav-text: #6B7280;
  --layout-nav-active-text: #111827;
  --layout-brand-bg: #111827;
  --layout-brand-icon: #FFFFFF;
  --layout-brand-text: #111827;
  --layout-brand-subtitle: #6B7280;

  /* Unified app theme tokens (single source for all pages/components) */
  --ink-bg-app: #F8FAFC;
  --ink-surface-1: #FFFFFF;
  --ink-surface-2: #F8FAFC;
  --ink-surface-3: #F3F4F6;
  --ink-border: #E5E7EB;
  --ink-border-strong: #D1D5DB;
  --ink-text-primary: #111827;
  --ink-text-secondary: #4B5563;
  --ink-text-muted: #6B7280;
  --ink-accent: #2563EB;
  --ink-accent-soft: #DBEAFE;
  --ink-success-bg: #F0FDF4;
  --ink-success-text: #15803D;
  --ink-warning-bg: #FFF7ED;
  --ink-warning-text: #C2410C;
  --ink-danger-bg: #FFF7F7;
  --ink-danger-text: #991B1B;

  height: 100vh;
  overflow: hidden;
  background-color: var(--layout-bg);
}

.main-layout--theme-warm {
  --layout-bg: #FCF8F3;
  --layout-header-bg: rgba(252, 248, 243, 0.92);
  --layout-header-border: #E9DDCF;
  --layout-nav-bg: #FFFDF9;
  --layout-nav-hover-bg: #F7EFE4;
  --layout-nav-text: #7A5C3E;
  --layout-nav-active-text: #4A3420;
  --layout-brand-bg: #6B4226;
  --layout-brand-icon: #FFFFFF;
  --layout-brand-text: #4A3420;
  --layout-brand-subtitle: #8B6E54;

  --ink-bg-app: #FCF8F3;
  --ink-surface-1: #FFFDF9;
  --ink-surface-2: #F7EFE4;
  --ink-surface-3: #F2E7D8;
  --ink-border: #E9DDCF;
  --ink-border-strong: #D9C7AF;
  --ink-text-primary: #4A3420;
  --ink-text-secondary: #6F4F33;
  --ink-text-muted: #8B6E54;
  --ink-accent: #A46B2A;
  --ink-accent-soft: #F5E6D3;
  --ink-success-bg: #ECF8F1;
  --ink-success-text: #1F6F4A;
  --ink-warning-bg: #FFF3E4;
  --ink-warning-text: #A55A17;
  --ink-danger-bg: #FFF1F1;
  --ink-danger-text: #A62A2A;
}

.main-layout--theme-dark {
  --layout-bg: #0F172A;
  --layout-header-bg: rgba(15, 23, 42, 0.94);
  --layout-header-border: #1E293B;
  --layout-nav-bg: #111827;
  --layout-nav-hover-bg: #1F2937;
  --layout-nav-text: #9CA3AF;
  --layout-nav-active-text: #F3F4F6;
  --layout-brand-bg: #EFF6FF;
  --layout-brand-icon: #1E293B;
  --layout-brand-text: #E5E7EB;
  --layout-brand-subtitle: #94A3B8;

  --ink-bg-app: #0F172A;
  --ink-surface-1: #111827;
  --ink-surface-2: #0F172A;
  --ink-surface-3: #1F2937;
  --ink-border: #233044;
  --ink-border-strong: #334155;
  --ink-text-primary: #E5E7EB;
  --ink-text-secondary: #CBD5E1;
  --ink-text-muted: #94A3B8;
  --ink-accent: #60A5FA;
  --ink-accent-soft: #1E3A5F;
  --ink-success-bg: #113B2B;
  --ink-success-text: #8CE3BA;
  --ink-warning-bg: #3D2F16;
  --ink-warning-text: #FCD34D;
  --ink-danger-bg: #3A1E1E;
  --ink-danger-text: #FCA5A5;
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

