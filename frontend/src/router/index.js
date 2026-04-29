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
        component: () => import('@/views/WorksList.vue'),
        meta: { title: '书架' }
      }
    ]
  },
  {
    path: '/works/:id',
    name: 'WritingStudio',
    component: () => import('@/views/WritingStudio.vue'),
    meta: { title: '写作页' }
  },
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

