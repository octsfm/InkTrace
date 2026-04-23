from __future__ import annotations

from fastapi.testclient import TestClient

from presentation.api.app import app


def test_chapter_detail_outline_get_put_roundtrip():
    client = TestClient(app)
    files = {
        "novel_file": (
            "novel.txt",
            "第1章 起始\n主角进入古城。\n\n第2章 冲突\n主角遭遇围攻。",
            "text/plain",
        ),
    }
    upload = client.post(
        "/api/projects/import/upload",
        data={"project_name": "章节细纲测试", "author": "测试作者", "genre": "xuanhuan", "auto_organize": "false"},
        files=files,
    )
    assert upload.status_code == 200
    novel_id = upload.json()["novel_id"]
    detail = client.get(f"/api/novels/{novel_id}")
    assert detail.status_code == 200
    chapter_id = detail.json()["chapters"][0]["id"]

    empty_resp = client.get(f"/api/chapters/{chapter_id}/detail-outline")
    assert empty_resp.status_code == 200
    assert empty_resp.json()["scenes"] == []

    save_resp = client.put(
        f"/api/chapters/{chapter_id}/detail-outline",
        json={
            "chapter_id": chapter_id,
            "notes": "本章需要强调冲突升级",
            "scenes": [
                {
                    "scene_no": 1,
                    "goal": "主角潜入古城",
                    "conflict": "守卫巡逻加强",
                    "turning_point": "发现密道入口",
                    "hook": "密道尽头出现黑影",
                    "foreshadow": "古城地图残页",
                    "target_words": 1200,
                }
            ],
        },
    )
    assert save_resp.status_code == 200
    payload = save_resp.json()
    assert payload["notes"] == "本章需要强调冲突升级"
    assert len(payload["scenes"]) == 1
    assert payload["scenes"][0]["goal"] == "主角潜入古城"

    get_resp = client.get(f"/api/chapters/{chapter_id}/detail-outline")
    assert get_resp.status_code == 200
    assert get_resp.json()["scenes"][0]["hook"] == "密道尽头出现黑影"
