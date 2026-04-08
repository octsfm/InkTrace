import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/novels', // Make NovelList the Dashboard
    children: [
      {
        path: 'novels',
        name: 'NovelList',
        component: () => import('@/views/novel/NovelList.vue'),
        meta: { title: '小说工作台' } // Rename to reflect dashboard
      },
      {
        path: 'import',
        name: 'NovelImport',
        component: () => import('@/views/novel/NovelImport.vue'),
        meta: { title: '导入小说' }
      },
      {
        path: 'config',
        name: 'LLMConfig',
        component: () => import('@/views/config/LLMConfig.vue'),
        meta: { title: '模型配置' }
      }
    ]
  },
  {
    // The Workspace is a top-level route because it has its own layout (4-column layout)
    // and should not be wrapped by MainLayout.vue
    path: '/novel/:id',
    name: 'NovelWorkspace',
    component: () => import('@/views/workspace/NovelWorkspace.vue'),
    meta: { title: '小说工作区' }
  }
]

const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:'

const router = createRouter({
  history: isFileProtocol ? createWebHashHistory() : createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - InkTrace Novel AI`
  next()
})

export default router
