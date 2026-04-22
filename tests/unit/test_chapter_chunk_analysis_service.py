import asyncio

from application.services.chapter_chunk_analysis_service import ChapterChunkAnalysisService


class _FakeChapterMemoryService:
    async def build_memories(self, **kwargs):
        text = str(kwargs.get("chapter_content") or "")
        return {
            "analysis_summary": {"summary": text[:80]},
            "continuation_memory": {"scene_summary": text[:60], "must_continue_points": [text[:20]]},
            "outline_draft": {"goal": "推进", "conflict": "冲突", "events": [text[:30]], "ending_hook": "悬念"},
            "used_fallback": False,
        }


def test_chunk_service_split_and_merge():
    service = ChapterChunkAnalysisService()
    chapter_text = "\n\n".join([f"第{i}段内容" + ("很长" * 700) for i in range(1, 7)])
    chunks = service.split_chapter(chapter_text, 4000)
    assert len(chunks) >= 2

    bundle = asyncio.run(
        service.analyze_by_chunks(
            chapter_memory_service=_FakeChapterMemoryService(),
            chapter_title="测试章节",
            chapter_content=chapter_text,
            constraints={},
            global_memory_summary="",
            global_outline_summary="",
            recent_chapter_summaries=[],
            require_model_success=False,
            chunk_size_chars=4000,
        )
    )
    assert int(bundle.get("chunk_count") or 0) >= 2
    assert isinstance(bundle.get("analysis_summary"), dict)
    assert isinstance(bundle.get("continuation_memory"), dict)
    assert isinstance(bundle.get("outline_draft"), dict)
