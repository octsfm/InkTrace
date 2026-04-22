from infrastructure.persistence.sqlite_v2_repo import SQLiteV2Repository


def test_batch_digest_persistence_supports_resume(tmp_path):
    db_path = str(tmp_path / "inktrace_resume.db")
    repo = SQLiteV2Repository(db_path)
    project_id = "proj_resume_1"
    repo.delete_organize_batch_digests(project_id)

    repo.save_organize_batch_digest(
        project_id=project_id,
        batch_no=1,
        chapter_from=1,
        chapter_to=4,
        digest_json={"digest": "第一批摘要"},
        token_estimate=120,
    )
    repo.save_organize_batch_digest(
        project_id=project_id,
        batch_no=2,
        chapter_from=5,
        chapter_to=8,
        digest_json={"digest": "第二批摘要"},
        token_estimate=132,
    )

    rows = repo.list_organize_batch_digests(project_id)
    assert len(rows) == 2
    assert rows[-1]["batch_no"] == 2
    assert rows[-1]["chapter_to"] == 8
    assert rows[-1]["digest_json"]["digest"] == "第二批摘要"


def test_stage_metrics_persistence(tmp_path):
    db_path = str(tmp_path / "inktrace_metrics.db")
    repo = SQLiteV2Repository(db_path)
    project_id = "proj_metrics_1"
    repo.save_organize_stage_metric(
        project_id=project_id,
        stage="global_analysis",
        model_name="moonshot-v1-8k",
        estimated_tokens=4200,
        budget_tokens=3800,
        status="budget_block",
        duration_ms=0,
        input_units=24,
        batch_no=6,
        batch_total=8,
        degrade_path="reduce_batch_size",
    )
    rows = repo.list_organize_stage_metrics(project_id)
    assert len(rows) >= 1
    assert rows[0]["stage"] == "global_analysis"
    assert rows[0]["status"] == "budget_block"
    assert rows[0]["degrade_path"] == "reduce_batch_size"
