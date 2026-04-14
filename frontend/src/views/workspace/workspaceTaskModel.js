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
  if (type.includes('structure')) return '结构任务'
  if (type.includes('organize')) return '整理任务'
  return task.typeLabel || '项目任务'
}

export const normalizeWorkspaceTaskResultType = (taskOrResult = {}) => {
  const value = String(taskOrResult.resultType || taskOrResult.result_type || '').trim().toLowerCase()
  if (['candidate', 'diff', 'issues', 'outline'].includes(value)) return value

  const type = String(taskOrResult.task_type || taskOrResult.type || '').trim().toLowerCase()
  if (type.includes('audit') || type.includes('analyze')) return 'issues'
  if (type.includes('rewrite') || type.includes('optimize')) return 'diff'
  if (type.includes('writing') || type.includes('generate') || type.includes('continue')) return 'candidate'
  return 'none'
}

export const buildWorkspaceTaskResultLabel = (taskOrResult = {}) => {
  const value = normalizeWorkspaceTaskResultType(taskOrResult)
  return buildWorkspaceResultLabel(value)
}

export const buildWorkspaceResultLabel = (resultType, options = {}) => {
  const fallbackLabel = options.noneLabel || '任务结果'
  const rewriteVariant = options.rewriteVariant || 'result'
  const value = String(resultType || '').trim().toLowerCase()
  if (value === 'candidate') return '候选稿'
  if (value === 'diff') return rewriteVariant === 'draft' ? '改写稿' : '改写结果'
  if (value === 'issues') return '问题结果'
  if (value === 'outline') return '大纲结果'
  if (value === 'none') return fallbackLabel
  return fallbackLabel
}

export const buildWorkspaceTaskActionPayload = (task = {}) => {
  const normalizedStatus = normalizeWorkspaceTaskStatus(task.status)
  const chapterId = String(task.chapter_id || task.chapterId || '')
  const targetArcId = String(task.target_arc_id || task.targetArcId || '')
  const resultType = normalizeWorkspaceTaskResultType(task)

  if (normalizedStatus === 'failed' && task.id === 'organize-task') {
    return { type: 'retry-organize' }
  }
  if (chapterId) {
    if (resultType === 'issues') {
      return { type: 'writing-result', chapterId, resultType: 'issues', taskId: String(task.id || task.task_id || '') }
    }
    if (resultType === 'candidate' || resultType === 'diff') {
      return { type: 'writing-result', chapterId, resultType, taskId: String(task.id || task.task_id || '') }
    }
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

export const buildWorkspaceTaskActionLabel = (task = {}) => {
  const chapterId = String(task?.chapter_id || task?.chapterId || '').trim()
  const targetArcId = String(task?.target_arc_id || task?.targetArcId || '').trim()
  const taskType = String(task?.task_type || task?.type || '').toLowerCase()
  const resultType = normalizeWorkspaceTaskResultType(task)
  if (chapterId && resultType === 'issues') return '查看问题单'
  if (chapterId && resultType === 'candidate') return '查看候选稿'
  if (chapterId && resultType === 'diff') return '查看改写稿'
  if (chapterId) return '打开章节'
  if (targetArcId) return '查看目标弧'
  if (taskType.includes('audit') || taskType.includes('analyze')) return '查看审查'
  if (FAILED_STATUSES.includes(String(task?.status || '').trim().toLowerCase())) return '查看失败任务'
  return '查看任务'
}

export const buildWorkspaceTaskTargetLabel = (task = {}, chapterTitle = '') => {
  const targetArcTitle = String(task?.target_arc_title || task?.targetArcId || task?.target_arc_id || '').trim()
  if (chapterTitle) {
    return `目标章节：${chapterTitle}`
  }
  if (targetArcTitle) {
    return `目标弧：${targetArcTitle}`
  }
  return '目标对象：项目任务'
}

export const buildWorkspaceTaskReasonText = (task = {}) => (
  String(task?.error_message || task?.error || task?.description || '').trim() || '当前未提供更详细的失败原因。'
)

export const buildWorkspaceTaskNextStepText = (task = {}) => {
  const status = normalizeWorkspaceTaskStatus(task?.status)
  const taskType = String(task?.task_type || task?.type || '').toLowerCase()
  if (status === 'failed') {
    if (String(task?.chapter_id || task?.chapterId || '').trim()) {
      return '建议先回到对应章节修复，再重新触发任务。'
    }
    if (String(task?.target_arc_id || task?.targetArcId || '').trim()) {
      return '建议先检查目标剧情弧状态，再重新推进相关任务。'
    }
    return '建议先查看失败任务筛选，再决定是否重试。'
  }
  if (status === 'running') {
    return '任务仍在进行中，可先回到对应对象继续处理。'
  }
  if (taskType.includes('audit') || taskType.includes('analyze')) {
    return '建议先看审查结果，再回到写作或结构页处理。'
  }
  return '可切回目标对象继续推进。'
}

export const resolveWorkspaceTaskTimestamp = (task = {}) => {
  const candidates = [
    task?.updated_at,
    task?.finished_at,
    task?.completed_at,
    task?.failed_at,
    task?.started_at,
    task?.created_at
  ]

  for (const value of candidates) {
    if (!value) continue
    const timestamp = new Date(value).getTime()
    if (Number.isFinite(timestamp) && timestamp > 0) {
      return timestamp
    }
  }

  return 0
}

export const buildWorkspaceTaskTraceItems = (task = {}, chapterTitle = '') => {
  const items = []
  const status = normalizeWorkspaceTaskStatus(task?.status)
  const taskType = String(task?.task_type || task?.type || '').toLowerCase()
  const progress = task?.progress ?? task?.percent
  const currentStage = String(task?.stage || task?.current_stage || '').trim()
  const targetArc = String(task?.target_arc_title || task?.target_arc_id || task?.targetArcId || '').trim()

  if (currentStage) {
    items.push({ label: '阶段', value: currentStage })
  }
  if (progress !== undefined && progress !== null && String(progress) !== '') {
    items.push({ label: '进度', value: `${progress}%` })
  }
  if (task?.current && task?.total) {
    items.push({ label: '批次', value: `${task.current}/${task.total}` })
  }
  if (String(task?.current_chapter_title || '').trim()) {
    items.push({ label: '当前章节', value: task.current_chapter_title })
  } else if (chapterTitle) {
    items.push({ label: '章节', value: chapterTitle })
  }
  if (targetArc) {
    items.push({ label: '目标弧', value: targetArc })
  }
  const resultType = normalizeWorkspaceTaskResultType(task)
  if (resultType && resultType !== 'none') {
    items.push({ label: '结果', value: buildWorkspaceTaskResultLabel(task), tone: 'primary' })
  }
  if (status === 'failed') {
    items.push({
      label: '失败',
      value: String(task?.error_message || task?.error || task?.message || '').trim() || '未提供更多错误信息',
      tone: 'danger'
    })
  } else if (status === 'running' && String(task?.message || '').trim()) {
    items.push({ label: '状态', value: String(task.message).trim(), tone: 'primary' })
  } else if ((taskType.includes('audit') || taskType.includes('analyze')) && String(task?.description || '').trim()) {
    items.push({ label: '审查', value: String(task.description).trim(), tone: 'primary' })
  }

  return items.slice(0, 4)
}

export const buildWorkspaceTaskRecord = (task = {}, options = {}) => {
  const rawStatus = options.status ?? task.status
  const status = normalizeWorkspaceTaskStatus(rawStatus)
  const chapterId = String(task.chapter_id || task.chapterId || options.chapterId || '').trim()
  const chapterTitle = options.chapterTitle || ''
  const title = options.title || task.title || task.label || task.name || '项目任务'
  const type = String(options.type || task.task_type || task.type || 'task')
  const subtitle = options.subtitle || [
    chapterTitle || (chapterId ? `章节 ${chapterId}` : ''),
    task.target_arc_title || task.target_arc_id || '',
    buildWorkspaceTaskTypeLabel(task)
  ].filter(Boolean).join(' · ')

  return {
    id: String(options.id || task.id || task.task_id || `${type}-${chapterId || 'workspace'}`),
    type,
    typeLabel: options.typeLabel || buildWorkspaceTaskTypeLabel(task),
    status,
    statusLabel: buildWorkspaceTaskStatusLabel(status),
    title,
    subtitle: subtitle || '项目任务',
    description: options.description || task.error_message || task.error || task.description || '用于驱动章节生成、审查与结构推进的项目任务。',
    targetLabel: options.targetLabel || buildWorkspaceTaskTargetLabel(task, chapterTitle),
    reasonText: options.reasonText || buildWorkspaceTaskReasonText(task),
    nextStepText: options.nextStepText || buildWorkspaceTaskNextStepText(task),
    hint: options.hint || (status === 'failed'
      ? '建议先回到对应对象处理后再恢复。'
      : '可切回对应章节或结构对象继续推进。'),
    actionLabel: options.actionLabel || buildWorkspaceTaskActionLabel(task),
    action: options.action || buildWorkspaceTaskActionPayload(task),
    chapterId,
    targetArcId: String(task.target_arc_id || task.targetArcId || ''),
    resultType: normalizeWorkspaceTaskResultType(task),
    resultTypeLabel: buildWorkspaceTaskResultLabel(task),
    timestamp: options.timestamp ?? resolveWorkspaceTaskTimestamp(task),
    traceItems: options.traceItems || buildWorkspaceTaskTraceItems(task, chapterTitle),
    source: options.source || 'project',
    raw: task
  }
}

export const buildWorkspaceTaskSummaryCounts = (tasks = []) => ({
  all: tasks.length,
  running: tasks.filter((item) => isWorkspaceTaskRunning(item?.status)).length,
  failed: tasks.filter((item) => isWorkspaceTaskFailed(item?.status)).length,
  completed: tasks.filter((item) => isWorkspaceTaskCompleted(item?.status)).length,
  audit: tasks.filter((item) => String(item?.type || '').toLowerCase().includes('audit')).length
})

export const buildWorkspaceTaskCenter = ({
  organizeProgress = {},
  chapterTasks = [],
  sessionTasks = [],
  currentTask = null,
  chapters = []
} = {}) => {
  const chapterTitleMap = new Map(
    (Array.isArray(chapters) ? chapters : []).map((item) => [String(item.id || ''), item.title || ''])
  )
  const records = []
  const organizeStatus = normalizeWorkspaceTaskStatus(organizeProgress?.status)

  records.push(buildWorkspaceTaskRecord(organizeProgress, {
    id: 'organize-task',
    type: 'organize',
    typeLabel: '整理任务',
    title: '全书整理任务',
    subtitle: `当前进度 ${organizeProgress?.progress ?? organizeProgress?.percent ?? 0}%`,
    description: organizeProgress?.error_message || '负责导入后整理、结构分析与相关写回。',
    targetLabel: '目标对象：全书结构与章节状态',
    reasonText: organizeProgress?.error_message || '当前未提供更详细的失败原因。',
    nextStepText: isWorkspaceTaskFailed(organizeStatus)
      ? '建议先查看失败原因，再重新整理。'
      : '可在任务控制台继续暂停、恢复或取消。',
    hint: isWorkspaceTaskFailed(organizeStatus)
      ? '建议先查看失败原因，再重试整理。'
      : '可在上方任务控制台执行暂停、恢复或取消。',
    actionLabel: isWorkspaceTaskFailed(organizeStatus) ? '重新整理' : '',
    action: isWorkspaceTaskFailed(organizeStatus) ? { type: 'retry-organize' } : null,
    status: organizeStatus || 'idle',
    source: 'organize'
  }))

  ;(Array.isArray(chapterTasks) ? chapterTasks : []).forEach((task, index) => {
    const chapterId = String(task.chapter_id || task.chapterId || '')
    records.push(buildWorkspaceTaskRecord(task, {
      id: String(task.id || task.task_id || `chapter-task-${index}`),
      chapterTitle: chapterTitleMap.get(chapterId) || '',
      source: 'project'
    }))
  })

  ;(Array.isArray(sessionTasks) ? sessionTasks : []).forEach((task) => {
    const chapterId = String(task.chapter_id || task.chapterId || '')
    records.push(buildWorkspaceTaskRecord(task, {
      id: String(task.id || ''),
      chapterTitle: chapterTitleMap.get(chapterId) || '',
      source: 'session',
      timestamp: resolveWorkspaceTaskTimestamp(task)
    }))
  })

  if (currentTask?.id) {
    const exists = records.some((item) => item.id === String(currentTask.id))
    if (!exists) {
      const chapterId = String(currentTask.chapter_id || currentTask.chapterId || '')
      records.push(buildWorkspaceTaskRecord(currentTask, {
        chapterTitle: chapterTitleMap.get(chapterId) || '',
        source: 'current',
        timestamp: 0
      }))
    }
  }

  const deduped = []
  const seen = new Set()
  records.forEach((item) => {
    if (!item?.id || seen.has(item.id)) return
    seen.add(item.id)
    deduped.push(item)
  })

  return {
    tasks: deduped,
    counts: buildWorkspaceTaskSummaryCounts(deduped),
    currentTaskId: String(currentTask?.id || ''),
    failedTasks: deduped.filter((item) => isWorkspaceTaskFailed(item.status)),
    runningTasks: deduped.filter((item) => isWorkspaceTaskRunning(item.status))
  }
}
