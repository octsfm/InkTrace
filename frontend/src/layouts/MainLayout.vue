<template>
  <div class="main-layout">
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
            :class="{ active: $route.path === '/novels' }"
            @click="$router.push('/novels')"
          >
            工作台
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: $route.path === '/import' }"
            @click="$router.push('/import')"
          >
            导入
          </button>
          <button
            type="button"
            class="nav-link"
            :class="{ active: $route.path === '/config' }"
            @click="$router.push('/config')"
          >
            配置
          </button>
        </nav>

        <div class="header-right">
          <el-button plain @click="$router.push('/config')">
            <el-icon><Setting /></el-icon>
            模型配置
          </el-button>
          <el-button type="primary" @click="$router.push('/import')">
            <el-icon><Plus /></el-icon>
            新建 / 导入小说
          </el-button>
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
import { Edit, Plus, Setting } from '@element-plus/icons-vue'
</script>

<style scoped>
.main-layout {
  height: 100vh;
  overflow: hidden;
  background-color: #F8FAFC;
}

.header {
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid #E5E7EB;
  background-color: rgba(248, 250, 252, 0.92);
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
  background-color: #111827;
  color: #ffffff;
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
  color: #111827;
}

.logo-subtitle {
  font-size: 12px;
  color: #6B7280;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border: 1px solid #E5E7EB;
  border-radius: 999px;
  background-color: #FFFFFF;
}

.nav-link {
  border: none;
  background: transparent;
  color: #6B7280;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: #111827;
  background-color: #F3F4F6;
}

.nav-link.active {
  color: #111827;
  background-color: #F3F4F6;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  height: calc(100vh - 69px);
  overflow-y: auto;
  background-color: #F8FAFC;
  padding: 0;
  overflow-y: auto;
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
