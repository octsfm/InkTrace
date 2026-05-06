import axios from 'axios'
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
const apiBaseURL = isElectron
  ? `http://localhost:${electronPort}/api`
  : '/api'

export const v1ApiBaseURL = `${apiBaseURL}/v1`

export const isVersionConflictError = (error) => (
  error?.response?.status === 409 &&
  ['version_conflict', 'asset_version_conflict'].includes(error?.response?.data?.detail)
)

export const normalizeV1ApiError = (error) => {
  if (isVersionConflictError(error)) {
    error.is_version_conflict = true
    error.conflict_payload = error.response?.data || null
    return error
  }
  return error
}

export const v1Api = axios.create({
  baseURL: v1ApiBaseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

v1Api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const normalized = normalizeV1ApiError(error)
    if (normalized.is_version_conflict) {
      return Promise.reject(normalized)
    }
    const detail = normalized?.response?.data?.detail
    ElMessage.error(detail || normalized.message || '请求失败')
    return Promise.reject(normalized)
  }
)

export const v1WorksApi = {
  list: () => v1Api.get('/works'),
  create: (data) => v1Api.post('/works', data),
  get: (id) => v1Api.get(`/works/${id}`),
  update: (id, data) => v1Api.put(`/works/${id}`, data),
  delete: (id) => v1Api.delete(`/works/${id}`)
}

export const v1ChaptersApi = {
  list: (workId) => v1Api.get(`/works/${workId}/chapters`).then((data) => data?.items ?? []),
  create: (workId, data) => v1Api.post(`/works/${workId}/chapters`, data),
  update: (chapterId, data) => v1Api.put(`/chapters/${chapterId}`, data),
  forceOverride: (chapterId, data) => v1Api.put(`/chapters/${chapterId}`, { ...data, force_override: true }),
  delete: (chapterId) => v1Api.delete(`/chapters/${chapterId}`),
  reorder: (workId, chapterIds) => v1Api.put(`/works/${workId}/chapters/reorder`, {
    items: (chapterIds || []).map((id, index) => ({
      id,
      order_index: index + 1
    }))
  })
}

export const v1SessionsApi = {
  get: (workId) => v1Api.get(`/works/${workId}/session`),
  save: (workId, data) => v1Api.put(`/works/${workId}/session`, data)
}

export const v1IOApi = {
  importTxt: ({ txtFile, title = '', author = '' }) => {
    const formData = new FormData()
    formData.append('file', txtFile)
    formData.append('title', title)
    formData.append('author', author)
    return v1Api.post('/io/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  exportTxt: (workId, params = {}) => axios.get(`${v1ApiBaseURL}/io/export/${workId}`, {
    params,
    responseType: 'blob'
  })
}

export const v1WritingAssetsApi = {
  getWorkOutline: (workId) => v1Api.get(`/works/${workId}/outline`),
  saveWorkOutline: (workId, data) => v1Api.put(`/works/${workId}/outline`, data),
  getChapterOutline: (chapterId) => v1Api.get(`/chapters/${chapterId}/outline`),
  saveChapterOutline: (chapterId, data) => v1Api.put(`/chapters/${chapterId}/outline`, data),

  listTimeline: (workId) => v1Api.get(`/works/${workId}/timeline-events`).then((data) => data?.items ?? []),
  createTimeline: (workId, data) => v1Api.post(`/works/${workId}/timeline-events`, data),
  updateTimeline: (eventId, data) => v1Api.put(`/timeline-events/${eventId}`, data),
  deleteTimeline: (eventId) => v1Api.delete(`/timeline-events/${eventId}`),
  reorderTimeline: (workId, items) => v1Api.put(`/works/${workId}/timeline-events/reorder`, { items }),

  listForeshadows: (workId, status = 'open') => v1Api.get(`/works/${workId}/foreshadows`, { params: { status } }).then((data) => data?.items ?? []),
  createForeshadow: (workId, data) => v1Api.post(`/works/${workId}/foreshadows`, data),
  updateForeshadow: (foreshadowId, data) => v1Api.put(`/foreshadows/${foreshadowId}`, data),
  deleteForeshadow: (foreshadowId) => v1Api.delete(`/foreshadows/${foreshadowId}`),

  listCharacters: (workId, keyword = '') => v1Api.get(`/works/${workId}/characters`, { params: { keyword } }).then((data) => data?.items ?? []),
  createCharacter: (workId, data) => v1Api.post(`/works/${workId}/characters`, data),
  updateCharacter: (characterId, data) => v1Api.put(`/characters/${characterId}`, data),
  deleteCharacter: (characterId) => v1Api.delete(`/characters/${characterId}`)
}
