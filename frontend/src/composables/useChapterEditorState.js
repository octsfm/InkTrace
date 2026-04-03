import { reactive } from 'vue'

export function useChapterEditorState() {
  return reactive({
    loading: false,
    saving: false,
    aiRunning: false,
    chapter: {
      id: '',
      title: '',
      content: ''
    },
    outline: {},
    chapterTask: {},
    chapterArcs: [],
    contextMeta: {},
    structuralDraft: null,
    detemplatedDraft: null,
    integrityCheck: null,
    activeDraftTab: 'structural',
    importDialogVisible: false,
    importText: '',
    errorMessage: ''
  })
}
