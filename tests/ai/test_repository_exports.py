from domain.repositories.ai import CitationLinkRepository, MultiChapterSessionRepository


def test_ai_repository_package_exports_multi_chapter_and_citation_repositories() -> None:
    assert MultiChapterSessionRepository.__name__ == "MultiChapterSessionRepository"
    assert CitationLinkRepository.__name__ == "CitationLinkRepository"
