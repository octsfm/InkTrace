from __future__ import annotations

from application.services.v1.chapter_service import ChapterService
from application.services.v1.io_service import IOService
from application.services.v1.session_service import SessionService
from application.services.v1.work_service import WorkService
from application.services.v1.writing_asset_service import WritingAssetService
from infrastructure.database.repositories import (
    ChapterOutlineRepo,
    ChapterRepo,
    CharacterRepo,
    EditSessionRepo,
    ForeshadowRepo,
    TimelineEventRepo,
    WorkOutlineRepo,
    WorkRepo,
)


def build_work_service() -> WorkService:
    return WorkService(
        work_repo=WorkRepo(),
        chapter_repo=ChapterRepo(),
    )


def build_chapter_service() -> ChapterService:
    return ChapterService(
        chapter_repo=ChapterRepo(),
        work_repo=WorkRepo(),
    )


def build_session_service() -> SessionService:
    return SessionService(
        session_repo=EditSessionRepo(),
        chapter_repo=ChapterRepo(),
        work_repo=WorkRepo(),
    )


def build_io_service() -> IOService:
    work_repo = WorkRepo()
    chapter_repo = ChapterRepo()
    return IOService(
        work_service=WorkService(work_repo=work_repo, chapter_repo=chapter_repo),
        work_repo=work_repo,
        chapter_repo=chapter_repo,
    )


def build_writing_asset_service() -> WritingAssetService:
    return WritingAssetService(
        work_repo=WorkRepo(),
        chapter_repo=ChapterRepo(),
        work_outline_repo=WorkOutlineRepo(),
        chapter_outline_repo=ChapterOutlineRepo(),
        timeline_event_repo=TimelineEventRepo(),
        foreshadow_repo=ForeshadowRepo(),
        character_repo=CharacterRepo(),
    )
