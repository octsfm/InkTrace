export const genreLabelMap = {
  xuanhuan: '玄幻',
  xianxia: '仙侠',
  dushi: '都市',
  kehuan: '科幻',
  lishi: '历史',
  wuxia: '武侠',
  qihuan: '奇幻',
  other: '其他'
}

export const novelStatusLabelMap = {
  active: '进行中',
  archived: '已归档',
  draft: '草稿'
}

export const chapterStatusLabelMap = {
  draft: '草稿',
  saved: '已保存',
  published: '已发布'
}

export const chapterFunctionLabelMap = {
  continue_crisis: '延续危机',
  advance_investigation: '推进调查',
  reveal_abnormal: '揭示异常',
  recover_foreshadow: '回收伏笔',
  transition: '过渡章节',
  explosion: '爆发章节'
}

export const organizeStatusLabelMap = {
  idle: '未开始',
  running: '整理中',
  pause_requested: '暂停请求中',
  paused: '已暂停',
  resume_requested: '继续请求中',
  cancelling: '取消中',
  cancelled: '已取消',
  done: '已完成',
  error: '失败'
}

export const organizeStageLabelMap = {
  idle: '未开始',
  running: '整理中',
  pause_requested: '暂停处理中',
  paused: '已暂停',
  resume_requested: '继续处理中',
  cancelling: '取消处理中',
  cancelled: '已取消',
  done: '已完成',
  error: '失败'
}

export const organizeStrategyLabelMap = {
  chapter_first: '按章节优先'
}

export const formatGenre = (value) => genreLabelMap[value] || value || '暂无'
export const formatNovelStatus = (value) => novelStatusLabelMap[value] || value || '暂无'
export const formatChapterStatus = (value) => chapterStatusLabelMap[value] || value || '暂无'
export const formatChapterFunction = (value) => chapterFunctionLabelMap[value] || value || '暂无'
export const formatOrganizeStatus = (value) => organizeStatusLabelMap[value] || value || '未知'
export const formatOrganizeStage = (value) => organizeStageLabelMap[value] || value || '暂无'
export const formatOrganizeStrategy = (value) => organizeStrategyLabelMap[value] || value || '暂无'
