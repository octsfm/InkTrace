CONTINUATION_HARD_RULES = [
    "必须承接上一章结尾场景、动作、情绪和钩子",
    "不得跳过当前危机状态",
    "不得突然时间跳跃",
    "不得突然讲解大量设定",
]

DETEMPLATE_HARD_RULES = [
    "不得删除关键剧情事件",
    "不得改变人物动机",
    "不得修改伏笔状态",
    "不得削弱结尾钩子",
    "不得过度文学化",
    "不得削弱章节推进感",
    "不得把连载文本改成慢叙事散文",
    "不得减少必要的信息密度",
]

DETEMPLATE_OPTIMIZATION_RULES = [
    "打乱过于均匀的句式节奏",
    "增加呼吸段、感官段、环境段",
    "增加少量真实反应，如误判、犹豫、反应滞后",
    "避免每一段都承担推进剧情的功能",
    "避免总结腔、说明腔、标准模板腔",
]

TASK_GENERATION_RULES = [
    "优先承接上一章最后钩子",
    "本章必须有明确功能定位",
    "本章必须指定伏笔动作",
    "本章必须指定结尾钩子强度",
]

CONTINUATION_MEMORY_RULES = [
    "只输出JSON",
    "必须提取下一章必须承接点",
    "immediate_threads 只保留下一章必须回应的线",
    "last_hook 必须明确提炼，不允许空泛",
]

INTEGRITY_CHECK_RULES = [
    "关键事件必须保留",
    "人物动机不能改变",
    "伏笔状态不能变化",
    "结尾钩子不能削弱",
    "章节推进不能被弱化",
    "标题必须仍与本章任务和章节功能一致",
    "去模板化后不能削弱连载推进感",
]

TITLE_BACKFILL_RULES = [
    "标题必须短、清晰、可连载",
    "标题不能为空",
    "标题不能只是章节编号",
    "标题不能剧透整章",
    "标题要与本章任务和钩子一致",
]

ARC_STAGE_TRANSITION_RULES = {
    "setup": ["目标", "阻力", "起点", "线索"],
    "early_push": ["升级", "代价", "阻力增强", "复杂"],
    "escalation": ["临界", "高压", "失控", "危机"],
    "crisis": ["抉择", "反转", "关键决定", "结构性改变"],
    "turning_point": ["兑现", "回收", "结果显性", "收束"],
    "payoff": ["余波", "善后", "后果", "重建"],
}

DEEP_PLANNING_TRIGGER_RULES = [
    "new_or_preferred_arc_selected",
    "target_arc_near_stage_transition",
    "consistency_warning_detected",
    "main_arc_stale_for_multiple_chapters",
    "active_arc_near_limit",
]
