import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const startMultiChapter = vi.fn()
const getMultiChapterProgress = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    startMultiChapter: (...args) => startMultiChapter(...args),
    getMultiChapterProgress: (...args) => getMultiChapterProgress(...args),
    advanceMultiChapter: vi.fn(),
    pauseMultiChapter: vi.fn(),
    resumeMultiChapter: vi.fn(),
    cancelMultiChapter: vi.fn()
  }
}))

import MultiChapterPanel from '../MultiChapterPanel.vue'

describe('MultiChapterPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    startMultiChapter.mockResolvedValue({ data: { session_id: 'session-1', status: 'running', target_chapters: 3 } })
    getMultiChapterProgress.mockResolvedValue({
      data: {
        session_id: 'session-1',
        status: 'waiting_user_decision',
        current_index: 1,
        target_chapters: 3,
        completed_count: 1,
        blocked_count: 0,
        per_chapter: [{ chapter_index: 1, status: 'completed', candidate_draft_id: 'draft-1' }]
      }
    })
  })

  it('starts from plain-language choices and never promises automatic apply', async () => {
    const wrapper = mount(MultiChapterPanel, {
      props: { visible: true, workId: 'work-1', chapterId: 'chapter-1' }
    })

    expect(wrapper.text()).toContain('准备几章新稿')
    expect(wrapper.text()).toContain('每章写完都会停下来等你')
    expect(wrapper.text()).not.toContain('一键全部放进正文')

    await wrapper.get('[data-test="multi-chapter-start"]').trigger('click')

    expect(startMultiChapter).toHaveBeenCalledWith(expect.objectContaining({
      work_id: 'work-1',
      start_chapter_id: 'chapter-1',
      target_chapters: 3,
      caller_type: 'user_action'
    }))
  })
})
