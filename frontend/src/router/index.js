import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

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
        path: 'novel/:id/workspace',
        component: () => import('@/views/workspace/NovelWorkspace.vue'),
        redirect: { name: 'WorkspaceOverview' },
        children: [
          {
            path: 'overview',
            name: 'WorkspaceOverview',
            component: () => import('@/views/workspace/WorkspaceOverview.vue'),
            meta: { title: '小说工作区 · 概览' }
          },
          {
            path: 'structure',
            name: 'WorkspaceStructure',
            component: () => import('@/views/workspace/WorkspaceStructureStudio.vue'),
            meta: { title: '小说工作区 · 结构台' }
          },
          {
            path: 'chapters',
            name: 'WorkspaceChapters',
            component: () => import('@/views/workspace/WorkspaceChapterManager.vue'),
            meta: { title: '小说工作区 · 章节台' }
          },
          {
            path: 'writing',
            name: 'WorkspaceWriting',
            component: () => import('@/views/workspace/WorkspaceWritingStudio.vue'),
            meta: { title: '小说工作区 · 写作台' }
          },
          {
            path: 'tasks',
            name: 'WorkspaceTasks',
            component: () => import('@/views/workspace/WorkspaceTasksAudit.vue'),
            meta: { title: '小说工作区 · 任务台' }
          }
        ]
      },
      {
        path: 'novel/:id/write',
        name: 'NovelWrite',
        component: () => import('@/views/novel/NovelWrite.vue'),
        meta: { title: '继续写作' }
      },
      {
        path: 'novel/:id/chapters/:chapterId/edit',
        name: 'ChapterEditor',
        component: () => import('@/views/novel/ChapterEditor.vue'),
        meta: { title: '章节编辑' }
      },
      {
        path: 'novel/:id/chapters/new',
        name: 'ChapterEditorNew',
        component: () => import('@/views/novel/ChapterEditor.vue'),
        meta: { title: '新建章节' }
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
      },
      {
        path: 'config',
        name: 'LLMConfig',
        component: () => import('@/views/config/LLMConfig.vue'),
        meta: { title: '模型配置' }
      }
    ]
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
