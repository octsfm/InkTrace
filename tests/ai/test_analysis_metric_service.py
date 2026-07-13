import asyncio
from pathlib import Path
from application.services.ai.analysis_metric_service import AnalysisMetricService
from infrastructure.persistence.sqlite_analysis_metric_repo import SQLiteAnalysisMetricRepository


class _Chapter:
    id="c1"; version=1; updated_at="now"; content="x"*20
class _Chapters:
    def list_by_work(self,work_id): return [_Chapter()]
class _Query:
    def __init__(self): self.calls=0
    async def _value(self,work_id): self.calls+=1; return {"work_id":work_id,"calls":self.calls}
    get_writing_stats=get_rhythm_analysis=get_dialogue_analysis=get_style_consistency=get_ai_usage_analysis=_value
    async def get_word_frequency(self,work_id,top_n=50): return await self._value(work_id)


def test_large_work_uses_fingerprint_cache_and_manual_refresh(tmp_path: Path):
    query=_Query(); service=AnalysisMetricService(query,SQLiteAnalysisMetricRepository(tmp_path/"db.sqlite"),_Chapters(),large_work_threshold=1)
    first=asyncio.run(service.get_writing_stats("work-1")); second=asyncio.run(service.get_writing_stats("work-1"))
    assert first==second and query.calls==1
    status=asyncio.run(service.refresh("work-1"))
    assert status["work_status"]=="ready" and len(status["metrics"])==6


def test_large_work_wrapper_reports_cached_and_stale_after_source_change(tmp_path: Path):
    chapters=_Chapters(); query=_Query(); service=AnalysisMetricService(query,SQLiteAnalysisMetricRepository(tmp_path/"db.sqlite"),chapters,large_work_threshold=1)
    first=asyncio.run(service.get_metric_response("work-1","overview"))
    _Chapter.version=2
    second=asyncio.run(service.get_metric_response("work-1","overview"))
    _Chapter.version=1
    assert first["source"]=="cached" and first["stale"] is False
    assert second["source"]=="cached" and second["stale"] is True
    assert second["data"]==first["data"]
