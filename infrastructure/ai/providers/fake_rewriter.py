from __future__ import annotations

from domain.services.ai.rewriter import RewriterPort


class FakeRewriter(RewriterPort):
    def rewrite(
        self,
        *,
        work_id: str,
        chapter_id: str,
        source_content: str,
        instruction_summary: str,
        source_context_pack_id: str,
    ) -> dict[str, object]:
        return {
            "rewritten_text": f"{source_content}\n\n{instruction_summary}".strip(),
            "revision_summary": instruction_summary,
            "addressed_issues": [instruction_summary] if instruction_summary else [],
            "provider_name": "fake",
            "model_name": "fake-writer",
        }

