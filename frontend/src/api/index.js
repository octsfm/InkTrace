import axios from 'axios'
import { ElMessage } from 'element-plus'

const isElectron = window.electronAPI !== undefined

const baseURL = isElectron 
  ? 'http://localhost:9527/api'
  : '/api'

const api = axios.create({
  baseURL: baseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const ERROR_MESSAGE_MAP = {
  NOVEL_NOT_FOUND: '未找到对应作品，请先创建或导入。',
  STRUCTURE_INPUT_INVALID: '故事结构整理失败，请检查内容后重试。',
  STRUCTURE_INTERNAL_ERROR: '故事结构整理失败，请稍后再试。',
  MEMORY_REQUIRED: '请先整理故事结构后再继续创作。',
  CONTINUE_FAILED: '当前章节创作失败，请调整目标后重试。',
  CONTINUE_INPUT_INVALID: '续写参数有误，请检查后重试。',
  CONTINUE_INTERNAL_ERROR: '续写失败，请稍后再试。'
}

api.interceptors.response.use(
  response => response.data,
  error => {
    const detail = error.response?.data?.detail
    let message = error.message || '请求失败'
    if (detail && typeof detail === 'object') {
      message = detail.user_message || ERROR_MESSAGE_MAP[detail.code] || detail.message || message
    } else if (detail) {
      message = detail
    }
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export const novelApi = {
  list: () => api.get('/novels/'),
  get: (id) => api.get(`/novels/${id}`),
  create: (data) => api.post('/novels/', data),
  delete: (id) => api.delete(`/novels/${id}`)
}

export const contentApi = {
  import: (data) => api.post('/content/import', data),
  memory: (novelId) => api.get(`/content/memory/${novelId}`),
  organize: (novelId) => api.post(`/content/organize/${novelId}`),
  analyzeStyle: (novelId) => api.get(`/content/style/${novelId}`),
  analyzePlot: (novelId) => api.get(`/content/plot/${novelId}`)
}

export const writingApi = {
  planPlot: (data) => api.post('/writing/plan', data),
  generate: (data) => api.post('/writing/generate', data),
  continue: (data) => api.post('/writing/continue', data)
}

export const exportApi = {
  export: (data) => api.post('/export/', data),
  download: (filePath) => `${baseURL}/export/download/${encodeURIComponent(filePath)}`
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
  create: (data) => api.post('/projects/', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  activate: (id) => api.post(`/projects/${id}/activate`),
  archive: (id) => api.post(`/projects/${id}/archive`)
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

export default api
