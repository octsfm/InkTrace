from pathlib import Path

from domain.entities.chapter_task import ChapterTask
from domain.entities.style_requirements import StyleRequirements
from infrastructure.persistence.sqlite_chapter_task_repo import SQLiteChapterTaskRepository
from infrastructure.persistence.sqlite_style_requirements_repo import SQLiteStyleRequirementsRepository


def test_style_requirements_repo_roundtrip(tmp_path: Path):
    db_path = str(tmp_path / "repo.db")
    repo = SQLiteStyleRequirementsRepository(db_path)
    repo.save(
        StyleRequirements(
            id="sr1",
            project_id="p1",
            author_voice_keywords=["紧张"],
            source_type="manual",
            version=2,
        )
    )
    item = repo.find_by_project_id("p1")
    assert item is not None
    assert item.author_voice_keywords == ["紧张"]
    assert item.source_type == "manual"
    assert item.version == 2


def test_chapter_task_repo_replace_and_find(tmp_path: Path):
    db_path = str(tmp_path / "repo.db")
    repo = SQLiteChapterTaskRepository(db_path)
    repo.replace_by_project(
        "p1",
        [
            ChapterTask(id="t1", chapter_id="c1", project_id="p1", branch_id="b1", chapter_number=1, chapter_function="推进"),
            ChapterTask(id="t2", chapter_id="c2", project_id="p1", branch_id="b1", chapter_number=2, chapter_function="回收"),
        ],
    )
    items = repo.find_by_project_id("p1")
    assert len(items) == 2
    assert items[0].chapter_number == 1
