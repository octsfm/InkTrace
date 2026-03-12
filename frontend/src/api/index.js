import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
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
  analyzeStyle: (novelId) => api.get(`/content/style/${novelId}`),
  analyzePlot: (novelId) => api.get(`/content/plot/${novelId}`)
}

export const writingApi = {
  planPlot: (data) => api.post('/writing/plan', data),
  generate: (data) => api.post('/writing/generate', data)
}

export const exportApi = {
  export: (data) => api.post('/export/', data),
  download: (filePath) => `/api/export/download/${encodeURIComponent(filePath)}`
}

export default api
