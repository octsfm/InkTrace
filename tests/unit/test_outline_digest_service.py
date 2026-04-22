from application.services.outline_digest_service import OutlineDigestService


def test_outline_digest_handles_large_outline_text():
    service = OutlineDigestService()
    long_outline = "\n".join([f"段落{i}：这是一段较长的大纲内容，用于测试摘要稳定性。" for i in range(1, 2000)])
    digest = service.build_digest(long_outline)
    assert isinstance(digest, dict)
    assert "premise" in digest
    assert "main_plot_lines" in digest
    assert "summary" in digest
    assert len(str(digest["summary"])) > 0
    assert len(str(digest["summary"])) <= 2400
