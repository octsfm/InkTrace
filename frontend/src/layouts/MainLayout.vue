<template>
  <el-container class="main-layout">
    <el-header class="header">
      <div class="header-left">
        <el-icon class="logo-icon"><Edit /></el-icon>
        <span class="logo-text">InkTrace Novel AI</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="$router.push('/projects')">
          <el-icon><Plus /></el-icon>
          新建项目
        </el-button>
      </div>
    </el-header>
    
    <el-container class="main-container">
      <el-aside width="220px" class="sidebar">
        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/projects">
            <el-icon><Folder /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/novels">
            <el-icon><Notebook /></el-icon>
            <span>小说列表</span>
          </el-menu-item>
          <el-menu-item index="/import">
            <el-icon><Upload /></el-icon>
            <span>导入小说</span>
          </el-menu-item>
        </el-menu>
        
        <div class="sidebar-footer">
          <el-tag type="info" size="small">v2.0.0</el-tag>
          <span class="author">作者：孔利群</span>
        </div>
      </el-aside>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
</script>

<style scoped>
.main-layout {
  height: 100vh;
  background-color: #f5f7fa;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.main-container {
  height: calc(100vh - 60px);
}

.sidebar {
  background-color: #fff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}

.sidebar-menu {
  border-right: none;
  height: calc(100% - 60px);
}

.sidebar-footer {
  padding: 15px;
  text-align: center;
  border-top: 1px solid #ebeef5;
}

.author {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
