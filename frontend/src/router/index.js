import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/works',
    children: [
      {
        path: 'works',
        name: 'WorksList',
        component: () => import('@/views/novel/NovelList.vue'),
        meta: { title: '书架' }
      }
    ]
  },
  {
    path: '/works/:id',
    name: 'NovelWorkspace',
    component: () => import('@/views/workspace/NovelWorkspace.vue'),
    meta: { title: '写作页' }
  },
  {
    path: '/novel/:id',
    redirect: (to) => ({
      path: `/works/${to.params.id}`,
      query: {
        ...to.query
      }
    })
  },
  {
    path: '/novel/:id/write',
    redirect: (to) => ({
      path: `/works/${to.params.id}`,
      query: {
        ...to.query,
        section: 'writing'
      }
    })
  },
  {
    path: '/novel/:id/chapters/:chapterId/edit',
    redirect: (to) => ({
      path: `/works/${to.params.id}`,
      query: {
        ...to.query,
        section: 'writing',
        chapterId: String(to.params.chapterId || '')
      }
    })
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
