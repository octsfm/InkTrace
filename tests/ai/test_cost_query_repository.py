from datetime import UTC, datetime
from pathlib import Path
from decimal import Decimal
import pytest

from domain.entities.ai.models import LLMCallLog, LLMCallStatus, LLMUsage
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore
from infrastructure.persistence.sqlite_cost_control_repo import SQLiteCostControlRepository


def _entry(request_id: str, *, started_at: str, job_id: str = "job-1") -> LLMCallLog:
    return LLMCallLog(prompt_key="writer",prompt_version="v1",work_id="work-1",job_id=job_id,model_role="writer",provider_name="provider",model_name="model",request_id=request_id,trace_id="trace",status=LLMCallStatus.SUCCEEDED,started_at=datetime.fromisoformat(started_at),finished_at=datetime.fromisoformat(started_at),usage=LLMUsage(input_tokens=100,output_tokens=50,total_tokens=150),estimated_cost=1.5,price_snapshot_json={"currency":"CNY","input_price_per_1k":1,"output_price_per_1k":1})


def test_cost_summary_trend_and_task_scope_use_sqlite_facts(tmp_path: Path):
    db=tmp_path/"inktrace.db"; store=FileLLMCallLogStore(tmp_path/"llm_call_logs.jsonl",database_path=db)
    store.append(_entry("req-1",started_at="2026-07-01T00:00:00+00:00"))
    repo=SQLiteCostControlRepository(db)
    summary=repo.get_summary("work-1","2026-07")
    trend=repo.get_trend("work-1","2026-07-01","2026-07-02")
    task=repo.get_task_cost("work-1","job_id","job-1")
    assert summary["estimated_cost"]=="1.500000"
    assert len(trend)==2 and sum(item["call_count"] for item in trend)==1
    assert task["total_tokens"]==150


def test_reconcile_only_inserts_missing_complete_jsonl_facts(tmp_path: Path):
    db=tmp_path/"inktrace.db"; replica=tmp_path/"llm_call_logs.jsonl"; entry=_entry("req-2",started_at="2026-07-02T00:00:00+00:00")
    replica.write_text(entry.model_dump_json()+"\n",encoding="utf-8")
    result=SQLiteCostControlRepository(db).reconcile_usage("work-1")
    assert result["inserted_count"]==1
    assert result["resolved"] is True


def test_budget_mutation_is_atomic_idempotent_and_conflict_safe(tmp_path: Path):
    repo=SQLiteCostControlRepository(tmp_path/"inktrace.db")
    args={"work_id":"work-1","budget_type":"monthly","enabled":True,"limit":Decimal("50"),"currency":"CNY","alert_threshold":Decimal("0.8"),"expected_revision":None,"user_id":"local-author","idempotency_key":"same-key"}
    first=repo.save_budget(**args); replay=repo.save_budget(**args)
    assert first==replay and first["revision"]==1
    with pytest.raises(ValueError,match="idempotency_conflict"):
        repo.save_budget(**{**args,"limit":Decimal("60")})
