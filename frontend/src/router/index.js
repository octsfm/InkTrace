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
        component: () => import('@/views/works/WorksList.vue'),
        meta: { title: 'Bookshelf' }
      }
    ]
  },
  {
    path: '/works/:id',
    name: 'WritingStudio',
    component: () => import('@/views/works/WritingStudio.vue'),
    meta: { title: 'Writing' }
  }
]

const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:'

const router = createRouter({
  history: isFileProtocol ? createWebHashHistory() : createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'Home'} - InkTrace`
  next()
})

export default router
