from __future__ import annotations

from domain.entities.ai.models import ContextPackSnapshot, WritingTask
from domain.services.ai.writer import WriterPort


class FakeWriter(WriterPort):
    def generate_candidate_text(self, *, context_pack: ContextPackSnapshot, writing_task: WritingTask) -> dict[str, str]:
        base_instruction = writing_task.user_instruction.strip() or "继续当前场景"
        summary = context_pack.summary.strip() or "基于现有上下文继续推进情节。"
        content = f"{base_instruction}。{summary[:120]}。新的段落从这里展开，人物继续行动并推进情节。"
        return {
            "content": content,
            "provider_name": "fake",
            "model_name": "fake-writer",
            "model_role": writing_task.model_role,
        }
