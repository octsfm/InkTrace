import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/projects',
    children: [
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/project/ProjectList.vue'),
        meta: { title: '项目管理' }
      },
      {
        path: 'novels',
        name: 'NovelList',
        component: () => import('@/views/novel/NovelList.vue'),
        meta: { title: '小说列表' }
      },
      {
        path: 'novel/:id',
        name: 'NovelDetail',
        component: () => import('@/views/novel/NovelDetail.vue'),
        meta: { title: '小说详情' }
      },
      {
        path: 'novel/:id/write',
        name: 'NovelWrite',
        component: () => import('@/views/novel/NovelWrite.vue'),
        meta: { title: '续写小说' }
      },
      {
        path: 'novel/:id/characters',
        name: 'CharacterManage',
        component: () => import('@/views/character/CharacterManage.vue'),
        meta: { title: '人物管理' }
      },
      {
        path: 'novel/:id/worldview',
        name: 'WorldviewManage',
        component: () => import('@/views/worldview/WorldviewManage.vue'),
        meta: { title: '世界观管理' }
      },
      {
        path: 'import',
        name: 'NovelImport',
        component: () => import('@/views/novel/NovelImport.vue'),
        meta: { title: '导入小说' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - InkTrace Novel AI`
  next()
})

export default router
