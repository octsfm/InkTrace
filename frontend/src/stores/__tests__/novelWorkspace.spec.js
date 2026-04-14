import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useNovelWorkspaceStore } from '../novelWorkspace'
import { useWorkspaceStore } from '../workspace'

const mockContinueWrite = vi.fn()
const mockChapterSave = vi.fn()

vi.mock('@/api', () => ({
  chapterEditorApi: {
    continueWrite: (...args) => mockContinueWrite(...args),
    save: (...args) => mockChapterSave(...args)
  },
  contentApi: {},
  novelApi: {},
  projectApi: {}
}))

describe('novelWorkspace store', () => {
  beforeEach(() => {
    mockContinueWrite.mockReset()
    mockChapterSave.mockReset()
    mockChapterSave.mockResolvedValue({})
    setActivePinia(createPinia())
  })

  it('extracts appended continuation text for preview while preserving full result', async () => {
    const store = useNovelWorkspaceStore()
    const workspaceStore = useWorkspaceStore()
    store.editor.chapter = {
      id: 'chapter-1',
      title: '第一章',
      content: '原始正文第一段。\n原始正文第二段。'
    }

    mockContinueWrite.mockResolvedValue({
      result_text: '原始正文第一段。\n原始正文第二段。\n这是新增续写内容。'
    })

    await store.runEditorAiAction('continue')

    expect(store.editor.structuralDraft).toMatchObject({
      title: '第一章',
      content: '这是新增续写内容。',
      full_content: '原始正文第一段。\n原始正文第二段。\n这是新增续写内容。',
      preview_mode: 'delta',
      source_action: 'continue'
    })
    expect(store.sessionTasks[0]).toMatchObject({
      type: 'writing',
      status: 'completed',
      chapterId: 'chapter-1',
      resultType: 'candidate'
    })
    expect(store.editor.resultState).toMatchObject({
      latestAction: 'continue',
      latestResultType: 'candidate',
      latestDraftType: 'structural',
      lastDecision: 'pending'
    })
    expect(store.taskCenter.counts.completed).toBe(1)
    expect(store.taskCenter.tasks.find((item) => item.id === store.sessionTasks[0].id)).toMatchObject({
      id: store.sessionTasks[0].id,
      resultType: 'candidate',
      resultTypeLabel: '候选稿'
    })
    expect(workspaceStore.currentTask).toMatchObject({
      status: 'completed',
      resultType: 'candidate'
    })

    await store.saveDraftResult({ type: 'structural' })
    expect(store.editor.resultState).toMatchObject({
      latestDraftType: 'structural',
      lastDecision: 'saved'
    })
  })

  it('records failed editor task into unified task center', async () => {
    const store = useNovelWorkspaceStore()
    store.editor.chapter = {
      id: 'chapter-2',
      title: '第二章',
      content: '正文'
    }
    mockContinueWrite.mockRejectedValueOnce(new Error('模型异常'))

    await expect(store.runEditorAiAction('continue')).rejects.toThrow('模型异常')

    expect(store.sessionTasks[0]).toMatchObject({
      type: 'writing',
      status: 'failed',
      error: '模型异常'
    })
    expect(store.editor.resultState).toMatchObject({
      latestAction: 'continue',
      latestResultType: 'candidate',
      lastDecision: 'error',
      lastError: '模型异常'
    })
    expect(store.taskCenter.counts.failed).toBe(1)
    expect(store.taskCenter.failedTasks[0]).toMatchObject({
      status: 'failed',
      reasonText: '模型异常'
    })
  })
})
