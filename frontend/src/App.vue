<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { onMounted } from 'vue'
import { useFeatureCapabilityStore } from '@/stores/useFeatureCapabilityStore'

const featureCapabilityStore = useFeatureCapabilityStore()

onMounted(() => {
  featureCapabilityStore.refresh()
})
</script>

<style>
#app {
  width: 100%;
  height: 100%;
}
</style>
