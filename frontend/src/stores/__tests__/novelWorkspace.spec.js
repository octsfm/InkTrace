import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useNovelWorkspaceStore } from '../novelWorkspace'

const mockContinueWrite = vi.fn()

vi.mock('@/api', () => ({
  chapterEditorApi: {
    continueWrite: (...args) => mockContinueWrite(...args)
  },
  contentApi: {},
  novelApi: {},
  projectApi: {}
}))

describe('novelWorkspace store', () => {
  beforeEach(() => {
    mockContinueWrite.mockReset()
    setActivePinia(createPinia())
  })

  it('extracts appended continuation text for preview while preserving full result', async () => {
    const store = useNovelWorkspaceStore()
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
  })
})
