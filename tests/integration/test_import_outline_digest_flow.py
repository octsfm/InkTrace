from infrastructure.persistence.sqlite_outline_document_repo import SQLiteOutlineDocumentRepository
from application.services.outline_digest_service import OutlineDigestService


def test_import_outline_digest_flow(tmp_path):
    db_path = str(tmp_path / "inktrace_outline.db")
    repo = SQLiteOutlineDocumentRepository(db_path)
    service = OutlineDigestService()
    novel_id = "novel_outline_1"
    raw_outline = "\n".join(
        [
            "主线：少年复仇并重建秩序",
            "世界规则：灵力有代价且不可逆转时空",
            "人物弧：主角从复仇走向守护",
            "伏笔：古卷、失踪导师、王城密库",
            "禁跳跃：战力不能无解释突增",
        ]
    )
    digest = service.build_digest(raw_outline)
    repo.save_document(
        novel_id=novel_id,
        raw_content=raw_outline,
        digest_json=digest,
        raw_hash="hash_1",
        digest_version=service.digest_version,
    )
    stored = repo.find_by_novel_id(novel_id)
    assert stored is not None
    assert stored["novel_id"] == novel_id
    assert stored["digest_version"] == service.digest_version
    assert isinstance(stored["digest_json"], dict)
    assert str(stored["digest_json"].get("premise") or "").strip()
