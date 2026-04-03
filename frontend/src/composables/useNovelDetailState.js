import { reactive } from 'vue'

export function useNovelDetailState() {
  return reactive({
    loading: false,
    novel: null,
    memoryView: null,
    outlineSummary: [],
    chapters: [],
    branches: [],
    branchLoading: false,
    organizeLoading: false,
    exportDialogVisible: false,
    errorMessage: ''
  })
}
