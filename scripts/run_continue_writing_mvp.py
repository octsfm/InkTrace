import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.agent_mvp import ContinueWritingTool, NovelMemory, TaskContext


def main() -> None:
    memory = NovelMemory()
    memory.merge_analysis(
        {
            "characters": [
                {"name": "孔凡圣", "traits": ["谨慎", "坚韧"], "relationships": {"苏清月": "同伴"}},
                {"name": "苏清月", "traits": ["冷静", "机警"], "relationships": {"孔凡圣": "信任"}}
            ],
            "world_settings": ["古城遗迹存在血脉机关", "符纹可记录祖先记忆"],
            "plot_threads": [
                {"title": "遗迹开启", "description": "主角拿到家族密卷", "status": "ongoing"}
            ],
            "writing_style": {"tone": "悬疑紧张", "pacing": "中快节奏", "narrative_style": "第三人称近距离"}
        }
    )

    tool = ContinueWritingTool()
    task_context = TaskContext(
        novel_id="novel-mvp-001",
        goal="第5章：密卷的真相",
        target_word_count=1200
    )
    result = tool.execute(
        task_context,
        {
            "goal": "第5章：密卷的真相",
            "memory": memory.to_agent_context()
        }
    )
    print(json.dumps(result.payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
