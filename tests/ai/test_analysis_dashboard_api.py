from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api import dependencies
from presentation.api.app import app


class _Service:
    async def get_metric_response(self, work_id, metric, top_n=50):
        mapping={"overview":self.get_writing_stats,"rhythm":self.get_rhythm_analysis,"dialogue":self.get_dialogue_analysis,"word_frequency":lambda value:self.get_word_frequency(value,top_n=top_n),"style":self.get_style_consistency,"ai_usage":self.get_ai_usage_analysis}
        return {"source":"cached","computed_at":"2026-07-13T00:00:00Z","stale":True,"data":await mapping[metric](work_id)}
    async def get_writing_stats(self, work_id):
        return {"work_id": work_id, "total_word_count": 1200, "total_chapters": 2}

    async def get_rhythm_analysis(self, work_id):
        return {"short_sentence_density": 0.3}

    async def get_dialogue_analysis(self, work_id):
        return {"dialogue_ratio": 0.4}

    async def get_word_frequency(self, work_id, top_n=50):
        return {"words": [], "top_n": top_n}

    async def get_style_consistency(self, work_id):
        return {"consistency_score": 0.8, "warning": None}

    async def get_ai_usage_analysis(self, work_id):
        return {"adoption_rate": 0.5, "disclaimer": "AI 常见词汇仅统计出现频率，不代表文本一定由 AI 生成"}


def test_analysis_dashboard_routes_are_read_only_and_plain(monkeypatch) -> None:
    monkeypatch.setenv("INKTRACE_P2_ENABLE_ANALYSIS_DASHBOARD", "1")
    monkeypatch.setattr(dependencies, "get_analysis_dashboard_query_service", lambda: _Service())
    client = TestClient(app)

    overview = client.get("/api/v2/ai/analysis-dashboard/overview", params={"work_id": "work-1"})
    usage = client.get("/api/v2/ai/analysis-dashboard/ai-usage", params={"work_id": "work-1"})

    assert overview.status_code == 200
    assert overview.json()["data"]["data"]["total_word_count"] == 1200
    assert overview.json()["data"]["source"] == "cached"
    assert overview.json()["data"]["stale"] is True
    assert usage.status_code == 200
    assert "不代表文本一定由 AI 生成" in usage.json()["data"]["data"]["disclaimer"]
