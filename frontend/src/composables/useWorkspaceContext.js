import { inject } from 'vue'

export const WORKSPACE_CONTEXT_KEY = Symbol('workspace-context')

export const useWorkspaceContext = () => {
  const context = inject(WORKSPACE_CONTEXT_KEY, null)
  if (!context) {
    throw new Error('Workspace context is not available.')
  }
  return context
}
