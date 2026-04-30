import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()
const mockPut = vi.fn()
const mockDelete = vi.fn()
const mockRawGet = vi.fn()
const responseUse = vi.fn()

vi.mock('axios', () => ({
  default: {
    get: (...args) => mockRawGet(...args),
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      interceptors: {
        response: { use: responseUse }
      }
    }))
  }
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn() }
}))

describe('V1.1 Workbench API 封装', () => {
  let api

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules()
    api = await import('../works')
  })

  it('uses /api/v1 as the Workbench API base path', () => {
    expect(api.v1ApiBaseURL).toBe('/api/v1')
  })

  it('wraps Works, Chapters, Sessions and IO endpoints with snake_case payloads', async () => {
    mockGet.mockResolvedValueOnce({ items: [{ id: 'chapter-1' }] })

    await api.v1WorksApi.list()
    await api.v1WorksApi.create({ title: '作品', author: '作者' })
    await api.v1ChaptersApi.update('chapter-1', {
      title: '标题',
      content: '正文',
      expected_version: 1
    })
    await api.v1ChaptersApi.reorder('work-1', ['chapter-2', 'chapter-1'])
    await api.v1SessionsApi.save('work-1', {
      active_chapter_id: 'chapter-1',
      cursor_position: 12,
      scroll_top: 34
    })

    expect(mockGet).toHaveBeenCalledWith('/works')
    expect(mockPost).toHaveBeenCalledWith('/works', { title: '作品', author: '作者' })
    expect(mockPut).toHaveBeenCalledWith('/chapters/chapter-1', {
      title: '标题',
      content: '正文',
      expected_version: 1
    })
    expect(mockPut).toHaveBeenCalledWith('/works/work-1/chapters/reorder', {
      items: [
        { id: 'chapter-2', order_index: 1 },
        { id: 'chapter-1', order_index: 2 }
      ]
    })
    expect(mockPut).toHaveBeenCalledWith('/works/work-1/session', {
      active_chapter_id: 'chapter-1',
      cursor_position: 12,
      scroll_top: 34
    })
  })

  it('recognizes version_conflict 409 without clearing caller-owned drafts', () => {
    const error = {
      response: {
        status: 409,
        data: {
          detail: 'version_conflict',
          server_version: 2,
          resource_type: 'chapter',
          resource_id: 'chapter-1'
        }
      }
    }

    const normalized = api.normalizeV1ApiError(error)

    expect(api.isVersionConflictError(error)).toBe(true)
    expect(normalized.is_version_conflict).toBe(true)
    expect(normalized.conflict_payload).toEqual(error.response.data)
  })

  it('exports TXT through the backend blob endpoint', async () => {
    await api.v1IOApi.exportTxt('work-1', { include_titles: false, gap_lines: 2 })

    expect(mockRawGet).toHaveBeenCalledWith('/api/v1/io/export/work-1', {
      params: { include_titles: false, gap_lines: 2 },
      responseType: 'blob'
    })
  })
})
