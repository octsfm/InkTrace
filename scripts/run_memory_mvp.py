import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.agent_mvp import NovelMemory


def main() -> None:
    memory = NovelMemory()

    chapter_1_analysis = {
        "characters": [
            {"name": "孔凡圣", "traits": ["谨慎", "果断"], "relationships": {"苏清月": "同伴"}},
            {"name": "苏清月", "traits": ["冷静"], "relationships": {"孔凡圣": "信任"}}
        ],
        "world_settings": ["古城遗迹存在血脉机关", "夜间灵雾会加重幻觉"],
        "plot_points": [
            {"title": "遗迹开启", "description": "主角触发石门符纹", "status": "ongoing"}
        ],
        "writing_style": {"tone": "悬疑紧张", "pacing": "中快节奏", "narrative_style": "第三人称近距离"}
    }

    chapter_2_analysis = {
        "characters": [
            {"name": "孔凡圣", "traits": ["谨慎", "坚韧"], "relationships": {"黑袍人": "敌对"}},
            {"name": "黑袍人", "traits": ["神秘"], "relationships": {"孔凡圣": "追捕"}}
        ],
        "world_settings": ["古城遗迹存在血脉机关", "符纹可记录祖先记忆"],
        "plot_threads": [
            {"title": "遗迹开启", "description": "石门后出现家族密卷", "status": "ongoing"},
            {"title": "黑袍追踪", "description": "黑袍人锁定主角踪迹", "status": "open"}
        ],
        "writing_style": {"tone": "压迫感增强", "pacing": "快节奏", "narrative_style": "第三人称近距离"}
    }

    memory.merge_analysis(chapter_1_analysis)
    merged = memory.merge_analysis(chapter_2_analysis)
    merged = memory.update_character_relationship("苏清月", "黑袍人", "警惕")
    merged = memory.add_world_setting("遗迹深层封印着未知生物")

    print(json.dumps(merged, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
