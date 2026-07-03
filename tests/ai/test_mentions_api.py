from __future__ import annotations

from fastapi.testclient import TestClient

from domain.entities.ai.models import (
    ChapterMention,
    MentionEntityType,
    MentionSource,
    MentionStatus,
    MentionSuggestion,
    MentionSummary,
)
from presentation.api import dependencies
from presentation.api.app import app


class _FakeMentionService:
    def __init__(self) -> None:
        self.saved_mentions: list[ChapterMention] = []

    def suggest(self, *, work_id: str, query: str, entity_types: list[str] | None = None, limit: int = 10) -> list[MentionSuggestion]:
        return [
            MentionSuggestion(
                entity_type=MentionEntityType.CHARACTER,
                entity_id="char_001",
                entity_name="张三",
                match_type="prefix",
                last_used_at="2026-07-03T10:00:00Z",
                summary_preview="主角，当前位于长安城。",
            )
        ]

    def get_by_chapter(self, chapter_id: str) -> list[ChapterMention]:
        return self.saved_mentions

    def replace_mentions(self, chapter_id: str, chapter_revision: int, mentions: list[ChapterMention]) -> list[ChapterMention]:
        self.saved_mentions = mentions
        return mentions

    def get_summary(self, mention_id: str) -> MentionSummary:
        return MentionSummary(
            mention_id=mention_id,
            entity_type=MentionEntityType.CHARACTER,
            entity_id="char_001",
            entity_name_snapshot="张三",
            entity_current_name="张三",
            summary_text="主角，当前位于长安城。",
            status=MentionStatus.ACTIVE,
            is_active=True,
            last_updated="2026-07-03T10:10:00Z",
        )


def _install_test_dependencies(monkeypatch):
    fake_service = _FakeMentionService()
    monkeypatch.setenv("INKTRACE_P2_ENABLE_MENTIONS", "1")
    monkeypatch.setattr(dependencies, "get_mention_service", lambda: fake_service)
    return fake_service


def test_mentions_api_supports_suggest_replace_query_and_summary(monkeypatch) -> None:
    fake_service = _install_test_dependencies(monkeypatch)
    client = TestClient(app)

    suggest_response = client.get("/api/v2/mentions/suggest", params={"work_id": "work_001", "q": "张"})
    assert suggest_response.status_code == 200
    assert suggest_response.json()["data"]["suggestions"][0]["entity_name"] == "张三"

    replace_response = client.put(
        "/api/v2/chapters/chapter_001/mentions",
        json={
            "chapter_revision": 3,
            "mentions": [
                {
                    "mention_id": "m_001",
                    "entity_type": "character",
                    "entity_id": "char_001",
                    "entity_name_snapshot": "张三",
                    "start_pos": 0,
                    "end_pos": 3,
                    "source": "user_input",
                    "ai_suggestion_id": "",
                }
            ],
        },
    )
    assert replace_response.status_code == 200
    assert replace_response.json()["data"]["mentions"][0]["mention_id"] == "m_001"
    assert fake_service.saved_mentions[0].source == MentionSource.USER_INPUT

    list_response = client.get("/api/v2/chapters/chapter_001/mentions")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["mentions"][0]["entity_id"] == "char_001"

    summary_response = client.get("/api/v2/mentions/m_001/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["data"]["summary"]["summary_text"] == "主角，当前位于长安城。"
