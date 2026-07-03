import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getOpeningAnalysis = vi.fn()
const getOpeningStatus = vi.fn()

vi.mock('@/api', () => ({
  aiApi: {
    getOpeningAnalysis,
    getOpeningStatus
  }
}))

vi.mock('@/config/p2FeatureFlags', () => ({
  isP2FeatureEnabled: (flagName) => flagName === 'enable_opening_agent'
}))

describe('useOpeningStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('hydrates opening preview payload and resets state when work changes', async () => {
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()

    await store.initializeForWork('work-1')
    store.hydratePreview({
      analysis: {
        analysis_summary: '前三章先用异常钟声建立悬念。'
      },
      strategy: {
        target_audience: '悬疑向读者'
      },
      riskLevel: 'high'
    })

    expect(store.featureEnabled).toBe(true)
    expect(store.workId).toBe('work-1')
    expect(store.analysis.analysis_summary).toContain('异常钟声')
    expect(store.strategy.target_audience).toBe('悬疑向读者')
    expect(store.riskLevel).toBe('high')

    await store.initializeForWork('work-2')

    expect(store.workId).toBe('work-2')
    expect(store.analysis.analysis_summary).toContain('前三章快速建立悬念')
    expect(store.strategy.target_audience).toContain('签约向')
    expect(store.riskLevel).toBe('warning')
  })

  it('supports granular preview updates and normalizes unsupported risk level', async () => {
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()

    await store.initializeForWork('work-1')

    store.setAnalysis({
      analysis_summary: '先用暴雨夜敲门声制造开篇钩子。'
    })
    store.setStrategy({
      target_audience: '男频悬疑读者'
    })
    store.setRiskLevel('unknown')

    expect(store.analysis.analysis_summary).toContain('暴雨夜敲门声')
    expect(store.analysis.hook_patterns).toContain('前 500 字引入异常事件')
    expect(store.strategy.target_audience).toBe('男频悬疑读者')
    expect(store.strategy.genre_positioning).toBe('都市悬疑')
    expect(store.riskLevel).toBe('warning')

    store.loadPreview({
      strategy: {
        opening_hook: '开篇先抛出失踪案现场'
      },
      riskLevel: 'HIGH'
    })

    expect(store.strategy.opening_hook).toContain('失踪案现场')
    expect(store.strategy.target_audience).toContain('签约向')
    expect(store.riskLevel).toBe('high')
  })

  it('keeps existing preview fields when analysis and strategy are updated incrementally', async () => {
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()

    await store.initializeForWork('work-1')
    store.loadPreview({
      analysis: {
        analysis_summary: '先用钟声建立开篇悬念。',
        conflict_patterns: ['主角被迫重返废弃灯塔']
      },
      strategy: {
        target_audience: '悬疑向女频读者',
        opening_hook: '第一段先出现异常钟声'
      },
      riskLevel: 'medium'
    })

    store.setAnalysis({
      hook_patterns: ['前 300 字出现异常钟声']
    })
    store.setStrategy({
      forbidden_similarity_notes: '避免直接复用废弃灯塔旧案设定'
    })

    expect(store.analysis.analysis_summary).toContain('先用钟声建立开篇悬念')
    expect(store.analysis.conflict_patterns).toContain('主角被迫重返废弃灯塔')
    expect(store.analysis.hook_patterns).toContain('前 300 字出现异常钟声')
    expect(store.strategy.target_audience).toBe('悬疑向女频读者')
    expect(store.strategy.opening_hook).toContain('第一段先出现异常钟声')
    expect(store.strategy.forbidden_similarity_notes).toContain('避免直接复用废弃灯塔旧案设定')
    expect(store.riskLevel).toBe('medium')
  })

  it('loads opening snapshot from analysis and status payloads incrementally', async () => {
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()

    await store.initializeForWork('work-1')

    store.loadSnapshot({
      analysis: {
        analysis_summary: '通过钟声、旧地图和海雾建立前三章悬念。'
      },
      strategy: {
        target_audience: '悬疑签约向读者',
        opening_hook: '第一段先抛出异常钟声'
      },
      risk_report: {
        risk_level: 'high'
      }
    })

    expect(store.analysis.analysis_summary).toContain('通过钟声、旧地图和海雾建立前三章悬念')
    expect(store.strategy.target_audience).toBe('悬疑签约向读者')
    expect(store.strategy.opening_hook).toContain('第一段先抛出异常钟声')
    expect(store.riskLevel).toBe('high')
    expect(store.phase).toBe('')
    expect(store.status).toBe('')
    expect(store.candidateDraftIds).toEqual([])

    store.loadSnapshot({
      phase: 'generate',
      status: 'running',
      candidate_draft_ids: ['cd_1', 'cd_2'],
      risk_report: {
        risk_level: 'medium'
      }
    })

    expect(store.analysis.analysis_summary).toContain('通过钟声、旧地图和海雾建立前三章悬念')
    expect(store.strategy.target_audience).toBe('悬疑签约向读者')
    expect(store.phase).toBe('generate')
    expect(store.status).toBe('running')
    expect(store.candidateDraftIds).toEqual(['cd_1', 'cd_2'])
    expect(store.riskLevel).toBe('medium')
  })

  it('loads opening snapshot from api for the current work', async () => {
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-02T10:45:00.000Z'))

    getOpeningAnalysis.mockResolvedValue({
      data: {
        analysis: {
          analysis_summary: '通过海雾和钟声建立开篇悬念。'
        },
        strategy: {
          target_audience: '悬疑签约向读者'
        },
        risk_report: {
          risk_level: 'high'
        }
      }
    })
    getOpeningStatus.mockResolvedValue({
      data: {
        phase: 'generate',
        status: 'running',
        candidate_draft_ids: ['cd_1']
      }
    })

    await store.initializeForWork('work-1')

    await expect(store.loadOpeningSnapshot()).resolves.toBe(true)

    expect(getOpeningAnalysis).toHaveBeenCalledWith('work-1')
    expect(getOpeningStatus).toHaveBeenCalledWith('work-1')
    expect(store.analysis.analysis_summary).toContain('海雾和钟声')
    expect(store.strategy.target_audience).toBe('悬疑签约向读者')
    expect(store.phase).toBe('generate')
    expect(store.status).toBe('running')
    expect(store.candidateDraftIds).toEqual(['cd_1'])
    expect(store.riskLevel).toBe('high')
    expect(store.snapshotLoaded).toBe(true)
    expect(store.snapshotLoadFailed).toBe(false)
    expect(store.lastSnapshotOutcome).toBe('succeeded')
    expect(store.lastSnapshotAt).toBe('2026-07-02T10:45:00.000Z')
    vi.useRealTimers()
  })

  it('keeps local preview when opening snapshot api fails', async () => {
    const { useOpeningStore } = await import('../useOpeningStore')
    const store = useOpeningStore()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-02T10:46:00.000Z'))

    await store.initializeForWork('work-1')
    store.loadPreview({
      analysis: {
        analysis_summary: '本地预览仍然保留钟声开篇摘要。'
      },
      strategy: {
        target_audience: '本地预览读者'
      },
      riskLevel: 'medium'
    })
    store.loadSnapshot({
      phase: 'analyze',
      status: 'pending',
      candidate_draft_ids: ['cd_local_1']
    })

    getOpeningAnalysis.mockRejectedValue(new Error('opening_analysis_failed'))

    await expect(store.loadOpeningSnapshot()).resolves.toBe(false)

    expect(getOpeningAnalysis).toHaveBeenCalledWith('work-1')
    expect(getOpeningStatus).not.toHaveBeenCalled()
    expect(store.analysis.analysis_summary).toContain('本地预览仍然保留钟声开篇摘要')
    expect(store.strategy.target_audience).toBe('本地预览读者')
    expect(store.phase).toBe('analyze')
    expect(store.status).toBe('pending')
    expect(store.candidateDraftIds).toEqual(['cd_local_1'])
    expect(store.riskLevel).toBe('medium')
    expect(store.snapshotLoaded).toBe(false)
    expect(store.snapshotLoadFailed).toBe(true)
    expect(store.lastSnapshotOutcome).toBe('failed')
    expect(store.lastSnapshotAt).toBe('2026-07-02T10:46:00.000Z')
    vi.useRealTimers()
  })
})
