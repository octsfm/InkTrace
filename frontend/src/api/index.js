import axios from 'axios'
import {
  DEFAULT_CHAPTER_COUNT,
  DEFAULT_TARGET_WORDS
} from '@/constants/uiDefaults'
import { ElMessage } from 'element-plus'

const isElectron = window.electronAPI !== undefined

const queryPort = (() => {
  try {
    const params = new URLSearchParams(window.location.search || '')
    return params.get('backend_port')
  } catch (error) {
    return null
  }
})()

const electronPort = queryPort || '9527'

const baseURL = isElectron
  ? `http://localhost:${electronPort}/api`
  : '/api'

const v1BaseURL = `${baseURL}/v1`

const api = axios.create({
  baseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const v1Api = axios.create({
  baseURL: v1BaseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const isCanceledError = (error) => (
  axios.isCancel?.(error) ||
  error?.code === 'ERR_CANCELED' ||
  error?.name === 'CanceledError'
)

const buildRequestId = () => {
  const ts = Math.floor(Date.now() / 1000)
  const rand = Math.random().toString(36).slice(2, 8)
  return `req_${ts}_${rand}`
}

const appendBatchSizeQuery = (basePath, batchSizeChapters) => {
  const size = Number(batchSizeChapters)
  if (!Number.isInteger(size) || size < 2 || size > 20) {
    return basePath
  }
  return `${basePath}&batch_size_chapters=${encodeURIComponent(size)}`
}

const ERROR_MESSAGE_MAP = {
  NOVEL_NOT_FOUND: '未找到对应作品，请先创建或导入。',
  STRUCTURE_INPUT_INVALID: '故事结构整理失败，请检查内容后重试。',
  STRUCTURE_INTERNAL_ERROR: '故事结构整理失败，请稍后再试。',
  MEMORY_REQUIRED: '请先整理故事结构后再继续创作。',
  CONTINUE_FAILED: '当前章节创作失败，请调整目标后重试。',
  CONTINUE_INPUT_INVALID: '续写参数有误，请检查后重试。',
  CONTINUE_INTERNAL_ERROR: '续写失败，请稍后再试。'
}

const formatValidationErrors = (detail) => {
  if (!Array.isArray(detail)) {
    return ''
  }
  const lines = detail
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return ''
      }
      const loc = Array.isArray(item.loc) ? item.loc.filter(Boolean).join('.') : ''
      const msg = item.msg || item.message || ''
      if (!loc && !msg) {
        return ''
      }
      return loc ? `${loc}: ${msg}` : msg
    })
    .filter(Boolean)
  if (!lines.length) {
    return ''
  }
  return `参数校验失败：${lines.join('；')}`
}

const resolveErrorMessage = (error) => {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) {
    const formatted = formatValidationErrors(detail)
    if (formatted) {
      return formatted
    }
  }
  if (detail && typeof detail === 'object') {
    return detail.user_message || ERROR_MESSAGE_MAP[detail.code] || detail.message || error.message || '请求失败'
  }
  if (detail) {
    return detail
  }
  return error.message || '请求失败'
}

const attachInterceptors = (client) => {
  client.interceptors.request.use((config) => {
    const requestId = buildRequestId()
    config.headers = config.headers || {}
    config.headers['X-Request-Id'] = requestId
    config.metadata = { ...(config.metadata || {}), requestId }
    return config
  })

  client.interceptors.response.use(
    (response) => response.data,
    (error) => {
      if (isCanceledError(error)) {
        return Promise.reject(error)
      }
      const responseRequestId = error?.response?.headers?.['x-request-id']
      const requestId = responseRequestId || error?.config?.metadata?.requestId || ''
      const message = resolveErrorMessage(error)
      if (requestId) {
        console.error('请求失败 request_id:', requestId)
      }
      if (error?.response?.status === 409) {
        error.userMessage = message
        return Promise.reject(error)
      }
      ElMessage.error(message)
      return Promise.reject(error)
    }
  )
}

attachInterceptors(api)
attachInterceptors(v1Api)

export const novelApi = {
  list: () => api.get('/novels/'),
  get: (id, config = {}) => api.get(`/novels/${id}`, {
    ...config,
    params: {
      include_chapters: false,
      ...(config?.params || {})
    }
  }),
  listChapters: (id, config = {}) => api.get(`/novels/${id}/chapters`, config).then((data) => data?.chapters ?? []),
  create: (data) => api.post('/novels/', data),
  delete: (id) => api.delete(`/novels/${id}`),
  createChapter: (novelId, data) => api.post(`/novels/${novelId}/chapters`, data),
  getChapter: (novelId, chapterId) => api.get(`/novels/${novelId}/chapters/${chapterId}`),
  updateChapter: (novelId, chapterId, data) => api.put(`/novels/${novelId}/chapters/${chapterId}`, data),
  deleteChapter: (novelId, chapterId) => api.delete(`/novels/${novelId}/chapters/${chapterId}`)
}

export const contentApi = {
  import: (data) => api.post('/content/import', data),
  importUpload: (formData) => api.post('/content/import/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  memory: (novelId) => api.get(`/content/memory/${novelId}`),
  organize: (novelId, forceRebuild = false, mode = 'full_reanalyze', batchSizeChapters = null) =>
    api.post(
      appendBatchSizeQuery(
        `/content/organize/${novelId}?force_rebuild=${forceRebuild ? 'true' : 'false'}&mode=${encodeURIComponent(mode)}`,
        batchSizeChapters
      ),
      {},
      { timeout: 0 }
    ),
  startOrganize: (novelId, forceRebuild = false, mode = 'full_reanalyze', batchSizeChapters = null) =>
    api.post(
      appendBatchSizeQuery(
        `/content/organize/start/${novelId}?force_rebuild=${forceRebuild ? 'true' : 'false'}&mode=${encodeURIComponent(mode)}`,
        batchSizeChapters
      )
    ),
  pauseOrganize: (novelId) => api.post(`/content/organize/pause/${novelId}`),
  stopOrganize: (novelId) => api.post(`/content/organize/stop/${novelId}`),
  resumeOrganize: (novelId, mode = '', batchSizeChapters = null) => {
    const basePath = `/content/organize/resume/${novelId}${mode ? `?mode=${encodeURIComponent(mode)}` : '?mode='}`
    return api.post(appendBatchSizeQuery(basePath, batchSizeChapters))
  },
  cancelOrganize: (novelId) => api.post(`/content/organize/cancel/${novelId}`),
  retryOrganize: (novelId, mode = 'full_reanalyze', batchSizeChapters = null) =>
    api.post(appendBatchSizeQuery(`/content/organize/retry/${novelId}?mode=${encodeURIComponent(mode)}`, batchSizeChapters)),
  organizeProgress: (novelId, config = {}) => api.get(`/content/organize/progress/${novelId}`, config),
  analyzeStyle: (novelId) => api.get(`/content/style/${novelId}`),
  analyzePlot: (novelId) => api.get(`/content/plot/${novelId}`)
}

export const writingApi = {
  planPlot: (data) => api.post('/writing/plan', data),
  branches: (data) => api.post('/writing/branches', data),
  generate: (data) => api.post('/writing/generate', data),
  continue: (data) => api.post('/writing/continue', data)
}

export const exportApi = {
  export: (data) => api.post('/export/', data),
  download: (filePath) => {
    const normalized = String(filePath || '')
      .split('/')
      .filter(Boolean)
      .map((segment) => encodeURIComponent(segment))
      .join('/')
    return `${baseURL}/export/download/${normalized}`
  }
}

export const vectorApi = {
  index: (novelId) => api.post(`/novels/${novelId}/vector/index`),
  status: (novelId) => api.get(`/novels/${novelId}/vector/status`),
  delete: (novelId) => api.delete(`/novels/${novelId}/vector/index`)
}

export const ragApi = {
  search: (novelId, query) => api.post(`/novels/${novelId}/rag/search`, { query }),
  context: (novelId, prompt) => api.post(`/novels/${novelId}/rag/context`, { prompt }),
  buildPrompt: (novelId, request) => api.post(`/novels/${novelId}/rag/prompt`, { request })
}

export const projectApi = {
  list: () => api.get('/projects/'),
  get: (id) => api.get(`/projects/${id}`),
  getByNovel: (novelId, config = {}) => api.get(`/projects/by-novel/${novelId}`, config),
  create: (data) => api.post('/projects/', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  activate: (id) => api.post(`/projects/${id}/activate`),
  archive: (id) => api.post(`/projects/${id}/archive`),
  importCreateEmpty: (data) => api.post('/projects/import', { ...data, import_mode: 'empty' }, { timeout: 0 }),
  importV2: (data) => api.post('/projects/import', { ...data, import_mode: data?.import_mode || 'full' }, { timeout: 0 }),
  importByChapterCompat: (data) => api.post('/projects/import', { ...data, import_mode: 'chapter_items' }, { timeout: 0 }),
  importV2Upload: (formData) => api.post('/projects/import/upload', formData, {
    timeout: 0,
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  importPreview: (data) => api.post('/content/import/preview', data),
  organizeV2: (projectId, data) => api.post(`/projects/${projectId}/organize`, data || { mode: 'full_reanalyze', rebuild_memory: true }, { timeout: 0 }),
  memoryV2: (projectId, config = {}) => api.get(`/projects/${projectId}/memory`, config).then((data) => data?.memory ?? data ?? {}),
  memoryViewV2: (projectId, config = {}) => api.get(`/projects/${projectId}/memory-view`, config).then((data) => data?.memory_view ?? data ?? {}),
  continuationContextV2: (projectId, params) => api.get(`/projects/${projectId}/continuation-context`, { params }),
  listBranchesV2: (projectId, config = {}) => api.get(`/projects/${projectId}/branches`, config),
  getStyleRequirements: (projectId) => api.get(`/projects/${projectId}/style-requirements`),
  updateStyleRequirements: (projectId, data) => api.put(`/projects/${projectId}/style-requirements`, data),
  extractStyleRequirements: (projectId, data) => api.post(`/projects/${projectId}/style-requirements/extract`, data || { sample_chapter_count: DEFAULT_CHAPTER_COUNT }),
  branchesV2: (projectId, data) => api.post(`/projects/${projectId}/branches`, data),
  chapterPlanV2: (projectId, data) => api.post(`/projects/${projectId}/chapter-plan`, data),
  chapterTasksV2: (projectId, config = {}) => api.get(`/projects/${projectId}/chapter-tasks`, config),
  plotArcsV2: (projectId) => api.get(`/projects/${projectId}/plot-arcs`),
  activePlotArcsV2: (projectId, config = {}) => api.get(`/projects/${projectId}/plot-arcs/active`, config),
  chapterArcsV2: (chapterId, config = {}) => api.get(`/projects/chapters/${chapterId}/arcs`, config),
  writePreviewV2: (projectId, data) => api.post(`/projects/${projectId}/write/preview`, data, { timeout: 0 }),
  writeCommitV2: (projectId, data) => api.post(`/projects/${projectId}/write/commit`, data, { timeout: 0 }),
  writeV2: (projectId, data) => api.post(`/projects/${projectId}/write`, data, { timeout: 0 }),
  refreshMemoryV2: (projectId, data) => api.post(`/projects/${projectId}/refresh-memory`, data)
}

export const templateApi = {
  list: () => api.get('/templates/'),
  get: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates/', data),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
  getByGenre: (genre) => api.get(`/templates/genre/${genre}`)
}

export const characterApi = {
  list: (novelId) => api.get(`/characters/novel/${novelId}`),
  get: (id) => api.get(`/characters/${id}`),
  create: (data) => api.post('/characters/', data),
  update: (id, data) => api.put(`/characters/${id}`, data),
  delete: (id) => api.delete(`/characters/${id}`)
}

export const worldviewApi = {
  get: (novelId) => api.get(`/worldview/novel/${novelId}`),
  create: (data) => api.post('/worldview/', data),
  update: (id, data) => api.put(`/worldview/${id}`, data),
  delete: (id) => api.delete(`/worldview/${id}`),
  addTechnique: (novelId, data) => api.post(`/worldview/${novelId}/techniques`, data),
  addFaction: (novelId, data) => api.post(`/worldview/${novelId}/factions`, data),
  addLocation: (novelId, data) => api.post(`/worldview/${novelId}/locations`, data)
}

const buildChapterAIRequest = (chapterId, action, data = {}) => ({
  chapter_id: chapterId,
  action,
  content: '',
  style: '',
  target_word_count: DEFAULT_TARGET_WORDS,
  outline: {},
  global_memory_summary: '',
  global_outline_summary: '',
  recent_chapter_summaries: [],
  ...data
})

export const chapterEditorApi = {
  get: (chapterId, config = {}) => api.get(`/chapters/${chapterId}`, config),
  getContext: (chapterId, config = {}) => api.get(`/chapters/${chapterId}/continuation-context`, config),
  save: (chapterId, data) => api.put(`/chapters/${chapterId}`, data),
  getOutline: (chapterId, config = {}) => api.get(`/chapters/${chapterId}/outline`, config),
  saveOutline: (chapterId, data) => api.put(`/chapters/${chapterId}/outline`, { chapter_id: chapterId, ...data }),
  organizeChapter: (chapterId, data = {}) => api.post(`/chapters/${chapterId}/organize`, data),
  getDetailOutline: (chapterId, config = {}) => api.get(`/chapters/${chapterId}/detail-outline`, config),
  saveDetailOutline: (chapterId, data) => api.put(`/chapters/${chapterId}/detail-outline`, { chapter_id: chapterId, ...data }),
  generateDetailOutline: (chapterId, data = { source: 'chapter_content' }) => api.post(`/chapters/${chapterId}/detail-outline/generate`, data),
  importChapter: (chapterId, data) => api.post(`/chapters/${chapterId}/import`, buildChapterAIRequest(chapterId, 'import', data)),
  optimize: (chapterId, data) => api.post(`/chapters/${chapterId}/ai/optimize`, buildChapterAIRequest(chapterId, 'optimize', data), { timeout: 0 }),
  continueWrite: (chapterId, data) => api.post(`/chapters/${chapterId}/ai/continue`, buildChapterAIRequest(chapterId, 'continue', data), { timeout: 0 }),
  rewriteStyle: (chapterId, data) => api.post(`/chapters/${chapterId}/ai/rewrite-style`, buildChapterAIRequest(chapterId, 'rewrite-style', data), { timeout: 0 }),
  rewriteSelection: (chapterId, data) => api.post(
    `/chapters/${chapterId}/ai/rewrite-selection`,
    buildChapterAIRequest(chapterId, 'rewrite-selection', {
      mode: 'selection',
      ...data
    }),
    { timeout: 0 }
  ),
  analyze: (chapterId, data) => api.post(`/chapters/${chapterId}/ai/analyze`, buildChapterAIRequest(chapterId, 'analyze', data), { timeout: 0 }),
  analyzeSelection: (chapterId, data) => api.post(
    `/chapters/${chapterId}/ai/analyze-selection`,
    buildChapterAIRequest(chapterId, 'analyze-selection', {
      mode: 'selection',
      ...data
    }),
    { timeout: 0 }
  ),
  generateFromOutline: (chapterId, data) => api.post(`/chapters/${chapterId}/ai/generate-from-outline`, buildChapterAIRequest(chapterId, 'generate-from-outline', data), { timeout: 0 })
}

export const v1WorksApi = {
  list: () => v1Api.get('/works'),
  create: (data) => v1Api.post('/works', data),
  get: (id) => v1Api.get(`/works/${id}`),
  delete: (id) => v1Api.delete(`/works/${id}`)
}

export const v1ChaptersApi = {
  list: (workId) => v1Api.get(`/works/${workId}/chapters`).then((data) => data?.items ?? []),
  create: (workId, data) => v1Api.post(`/works/${workId}/chapters`, data),
  update: (chapterId, data) => v1Api.put(`/chapters/${chapterId}`, data),
  forceOverride: (chapterId, data) => v1Api.put(`/chapters/${chapterId}`, { ...data, force_override: true }),
  delete: (chapterId) => v1Api.delete(`/chapters/${chapterId}`),
  reorder: (workId, chapterIds) => v1Api.put(`/works/${workId}/chapters/reorder`, { chapter_ids: chapterIds })
}

export const v1SessionsApi = {
  get: (workId) => v1Api.get(`/works/${workId}/session`),
  save: (workId, data) => v1Api.put(`/works/${workId}/session`, data)
}

export const v1IOApi = {
  importTxt: (data) => v1Api.post('/io/import', data),
  exportTxt: (workId, params = {}) => v1Api.get(`/io/export/${workId}`, { params })
}

export default api
