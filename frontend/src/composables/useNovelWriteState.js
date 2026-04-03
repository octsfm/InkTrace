import { reactive } from 'vue'

export function useNovelWriteState() {
  return reactive({
    loading: false,
    branchLoading: false,
    planLoading: false,
    previewLoading: false,
    commitLoading: false,
    selectedBranchId: '',
    planningMode: 'light_planning',
    targetArcId: '',
    chapterCount: 3,
    targetWords: 2500,
    branches: [],
    plans: [],
    previewResult: {
      chapterTask: null,
      structuralDraft: null,
      detemplatedDraft: null,
      integrityCheck: null,
      revisionAttempts: [],
      usedStructuralFallback: false,
      planningReason: '',
      arcStageBefore: '',
      arcStageAfterExpected: ''
    },
    generatedBatch: {
      generatedChapters: [],
      latestChapter: null,
      latestStructuralDraft: null,
      latestDetemplatedDraft: null,
      latestDraftIntegrityCheck: null,
      usedStructuralFallback: false,
      chapterSaved: false,
      memoryRefreshed: false,
      savedChapterIds: [],
      planningReason: '',
      arcStageBefore: '',
      arcStageAfterExpected: '',
      arcStageAfterActual: '',
      arcStageAdvanced: false
    },
    errorMessage: ''
  })
}
