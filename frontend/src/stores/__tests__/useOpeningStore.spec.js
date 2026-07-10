import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const createOpeningBrief = vi.fn()
const generateOpeningDirections = vi.fn()
const addOpeningReferences = vi.fn()
const confirmOpeningDirection = vi.fn()
const reviseOpeningDirection = vi.fn()
const generateOpeningDrafts = vi.fn()
const getLatestOpening = vi.fn()

vi.mock('@/api', () => ({ aiApi: {
  createOpeningBrief, addOpeningReferences, generateOpeningDirections, confirmOpeningDirection, reviseOpeningDirection,
  generateOpeningDrafts, getLatestOpening
} }))
vi.mock('@/config/p2FeatureFlags', () => ({ isP2FeatureEnabled: () => true }))

describe('useOpeningStore v2', () => {
  beforeEach(() => { vi.clearAllMocks(); setActivePinia(createPinia()) })

  it('runs the human flow with a real user direction confirmation', async () => {
    createOpeningBrief.mockResolvedValue({ data: { brief_id: 'ob_1', work_id: 'work-1', story_premise: '悬疑故事', status: 'ready' } })
    generateOpeningDirections.mockResolvedValue({ data: { batch_id: 'odb_1', status: 'waiting_direction_choice', directions: [{ direction_id: 'od_1', name: '先抛谜团', summary: '先出现异常事件', chapter_goals: ['异常', '追查', '反转'] }] } })
    confirmOpeningDirection.mockResolvedValue({ data: { direction_id: 'od_1', name: '先抛谜团', status: 'confirmed' } })
    generateOpeningDrafts.mockResolvedValue({ data: { draft_batch_id: 'db_1', status: 'waiting_draft_review', chapter_results: [{ chapter_no: 1, status: 'waiting_review', candidate_draft_id: 'cd_1' }] } })
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()
    await store.initializeForWork('work-1')
    await store.createBrief({ storyPremise: '悬疑故事', protagonistDesire: '找真相', thirdChapterExpectation: '期待反转' })
    await store.generateDirections()
    await store.confirmDirection('od_1')
    await store.generateDrafts()

    expect(confirmOpeningDirection).toHaveBeenCalledWith('od_1', expect.objectContaining({ caller_type: 'user_action', user_action: true }))
    expect(store.candidateDraftIds).toEqual(['cd_1'])
    expect(store.strategy.target_audience).toBe('先抛谜团')
  })

  it('loads the latest resumable business state by work', async () => {
    getLatestOpening.mockResolvedValue({ data: { brief: { brief_id: 'ob_2', story_premise: '成长故事' }, direction_batch: null, draft_batch: null } })
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()
    await store.initializeForWork('work-2')
    await expect(store.loadOpeningSnapshot()).resolves.toBe(true)
    expect(getLatestOpening).toHaveBeenCalledWith('work-2')
    expect(store.analysis.analysis_summary).toContain('成长故事')
  })

  it('uploads authorized references after the brief and before directions', async () => {
    createOpeningBrief.mockResolvedValue({ data: { brief_id: 'ob_ref', work_id: 'work-1', status: 'ready' } })
    addOpeningReferences.mockResolvedValue({ data: { reference_session_id: 'ors_1', status: 'analyzed' } })
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()
    await store.initializeForWork('work-1')
    await store.createBrief({ storyPremise: '故事', protagonistDesire: '目标', thirdChapterExpectation: '期待' })
    await store.addReferences([{ title: '参考', chaptersText: ['第一章'] }], true)
    expect(addOpeningReferences).toHaveBeenCalledWith('ob_ref', expect.objectContaining({
      rights_confirmed: true,
      references: [{ title: '参考', chapters_text: ['第一章'] }]
    }))
  })

  it('keeps a revised direction as a new selectable version', async () => {
    reviseOpeningDirection.mockResolvedValue({ data: {
      direction_id: 'od_2', parent_direction_id: 'od_1', revision_no: 2,
      name: '我的方向', summary: '从日常异常开始', chapter_goals: ['异常', '追查', '反转'], status: 'proposed'
    } })
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()
    store.directionBatch = { batch_id: 'odb_1', directions: [{ direction_id: 'od_1', name: '原方向' }] }
    const revised = await store.reviseDirection('od_1', {
      name: '我的方向', summary: '从日常异常开始', chapterGoals: ['异常', '追查', '反转'], advantages: [], risks: []
    })
    expect(reviseOpeningDirection).toHaveBeenCalledWith('od_1', expect.objectContaining({
      chapter_goals: ['异常', '追查', '反转']
    }))
    expect(store.directionBatch.directions.at(-1)).toEqual(revised)
  })
})
