const FAILED_STATUSES = ['failed', 'error']
const COMPLETED_STATUSES = ['completed', 'success', 'done']

export const normalizeWorkspaceTaskStatus = (status) => {
  const value = String(status || '').trim().toLowerCase()
  if (!value) return 'idle'
  if (FAILED_STATUSES.includes(value)) return 'failed'
  if (COMPLETED_STATUSES.includes(value)) return 'completed'
  if (value === 'running') return 'running'
  if (value === 'paused') return 'paused'
  return value
}

export const buildWorkspaceTaskStatusLabel = (status) => {
  const normalized = normalizeWorkspaceTaskStatus(status)
  if (normalized === 'running') return '运行中'
  if (normalized === 'paused') return '已暂停'
  if (normalized === 'completed') return '已完成'
  if (normalized === 'failed') return '失败'
  if (normalized === 'idle') return '待命'
  return normalized
}

export const isWorkspaceTaskFailed = (status) => normalizeWorkspaceTaskStatus(status) === 'failed'

export const isWorkspaceTaskCompleted = (status) => normalizeWorkspaceTaskStatus(status) === 'completed'

export const isWorkspaceTaskRunning = (status) => normalizeWorkspaceTaskStatus(status) === 'running'

export const buildWorkspaceTaskTypeLabel = (task = {}) => {
  const type = String(task.task_type || task.type || '').toLowerCase()
  if (type.includes('audit') || type.includes('analyze')) return '审查任务'
  if (type.includes('rewrite')) return '改写任务'
  if (type.includes('writing')) return '写作任务'
  if (type.includes('organize')) return '整理任务'
  return task.typeLabel || '项目任务'
}

export const buildWorkspaceTaskActionPayload = (task = {}) => {
  const normalizedStatus = normalizeWorkspaceTaskStatus(task.status)
  const chapterId = String(task.chapter_id || task.chapterId || '')
  const targetArcId = String(task.target_arc_id || task.targetArcId || '')

  if (normalizedStatus === 'failed' && task.id === 'organize-task') {
    return { type: 'retry-organize' }
  }
  if (chapterId) {
    return { type: 'chapter', chapterId }
  }
  if (targetArcId) {
    return {
      type: 'arc',
      arcId: targetArcId,
      title: task.target_arc_title || task.targetTitle || task.title || ''
    }
  }
  if (normalizedStatus === 'failed') {
    return { type: 'task-filter', filter: 'failed' }
  }
  if (String(task.task_type || task.type || '').toLowerCase().includes('audit')) {
    return { type: 'task-filter', filter: 'audit' }
  }
  return { type: 'section', section: 'tasks' }
}
