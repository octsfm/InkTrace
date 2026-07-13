from __future__ import annotations

import json
import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from domain.repositories.ai.cost_control_repository import CostControlRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect
from infrastructure.database.repositories.ai.file_llm_call_log_store import FileLLMCallLogStore
from domain.entities.ai.models import LLMCallLog


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


class SQLiteCostControlRepository(CostControlRepository):
    def __init__(self, database_path: Path | str | None = None) -> None:
        self._database_path = Path(database_path).resolve() if database_path else get_database_path()

    def get_summary(self, work_id: str, month: str) -> dict[str, object]:
        start_at, end_at = self._month_bounds(month)
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(
                "SELECT input_tokens, output_tokens, total_tokens, estimated_cost_text, cost_currency, status, usage_status, cost_status "
                "FROM llm_call_logs WHERE work_id=? AND started_at>=? AND started_at<? ORDER BY started_at",
                (work_id, start_at, end_at),
            ).fetchall()
        finally:
            conn.close()
        input_tokens = output_tokens = total_tokens = 0
        known_cost = Decimal("0")
        unknown_cost_count = unknown_usage_count = 0
        for row in rows:
            if row[0] is None or row[1] is None or row[2] is None:
                unknown_usage_count += 1
            else:
                input_tokens += int(row[0]); output_tokens += int(row[1]); total_tokens += int(row[2])
            if str(row[7] or "unknown") != "known":
                unknown_cost_count += 1
            else:
                known_cost += Decimal(str(row[3] or "0"))
        cost_status = "known" if rows and unknown_cost_count == 0 else "unknown" if unknown_cost_count else "empty"
        usage_status = "complete" if rows and unknown_usage_count == 0 else "partial" if rows else "empty"
        return {
            "month": month,
            "call_count": len(rows),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": _money(known_cost) if cost_status == "known" else None,
            "currency": self._single_currency(rows) if cost_status == "known" else None,
            "cost_completeness": cost_status,
            "usage_completeness": usage_status,
            "unknown_cost_call_count": unknown_cost_count,
            "unknown_usage_call_count": unknown_usage_count,
        }

    def list_details(self, work_id: str, month: str, limit: int, offset: int) -> dict[str, object]:
        start_at, end_at = self._month_bounds(month)
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(
                "SELECT provider_name, model_name, status, input_tokens, output_tokens, total_tokens, estimated_cost, price_snapshot_json, started_at "
                "FROM llm_call_logs WHERE work_id=? AND started_at>=? AND started_at<? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                (work_id, start_at, end_at, limit, offset),
            ).fetchall()
        finally:
            conn.close()
        items = []
        for row in rows:
            snapshot = json.loads(row[7] or "{}")
            known = row[3] is not None and bool(snapshot)
            items.append({
                "provider_name": row[0], "model_name": row[1], "status": row[2],
                "input_tokens": row[3], "output_tokens": row[4], "total_tokens": row[5],
                "estimated_cost": _money(Decimal(str(row[6] or "0"))) if known else None,
                "currency": snapshot.get("currency") if known else None, "started_at": row[8],
            })
        return {"items": items, "limit": limit, "offset": offset}

    def get_budget(self, work_id: str, budget_type: str) -> dict[str, object] | None:
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            row = conn.execute("SELECT * FROM cost_budgets WHERE work_id=? AND budget_type=?", (work_id, budget_type)).fetchone()
        finally:
            conn.close()
        if work_id and (row is None or bool(row[4])):
            inherited=self.get_budget("", budget_type)
            return {**inherited,"source":"global","inherit_global":True} if inherited else None
        return {**self._budget_dict(row),"source":"work" if work_id else "global"} if row else None

    def save_budget(self, *, work_id: str, budget_type: str, enabled: bool, limit: Decimal, currency: str, alert_threshold: Decimal, expected_revision: int | None, user_id: str, idempotency_key: str, inherit_global: bool = False) -> dict[str, object]:
        request_data={"kind":"budget","work_id":work_id,"budget_type":budget_type,"enabled":enabled,"limit":_money(limit),"currency":currency,"alert_threshold":_money(alert_threshold),"expected_revision":expected_revision,"inherit_global":inherit_global}
        replay, mutation = self._prepare_mutation(idempotency_key,user_id,request_data)
        if replay is not None: return replay
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            current = conn.execute("SELECT revision, budget_id FROM cost_budgets WHERE work_id=? AND budget_type=?", (work_id, budget_type)).fetchone()
            if current and expected_revision is not None and int(current[0]) != expected_revision:
                raise ValueError("P2_BUDGET_CONFLICT")
            revision = int(current[0]) + 1 if current else 1
            budget_id = str(current[1]) if current else f"budget_{uuid.uuid4().hex}"
            now = datetime.now(UTC).isoformat()
            conn.execute(
                "INSERT INTO cost_budgets(budget_id,work_id,budget_type,enabled,inherit_global,limit_value,currency,alert_threshold,revision,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(work_id,budget_type) DO UPDATE SET enabled=excluded.enabled,inherit_global=excluded.inherit_global,limit_value=excluded.limit_value,currency=excluded.currency,alert_threshold=excluded.alert_threshold,revision=excluded.revision,updated_at=excluded.updated_at",
                (budget_id, work_id, budget_type, int(enabled), int(bool(inherit_global and work_id)), _money(limit), currency, _money(alert_threshold), revision, now),
            )
            row = conn.execute("SELECT * FROM cost_budgets WHERE work_id=? AND budget_type=?", (work_id, budget_type)).fetchone()
            result=self._budget_dict(row)
            self._insert_pending_receipt(conn,mutation,result)
            conn.commit()
        finally:
            conn.close()
        self._complete_mutation(mutation,result)
        return result

    def list_prices(self, work_id: str, provider_name: str = "", model_name: str = "") -> list[dict[str, object]]:
        clauses = ["work_id=?"]; params: list[object] = [work_id]
        if provider_name: clauses.append("provider_name=?"); params.append(provider_name)
        if model_name: clauses.append("model_name=?"); params.append(model_name)
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            rows = conn.execute(f"SELECT * FROM model_price_policies WHERE {' AND '.join(clauses)} ORDER BY provider_name,model_name", params).fetchall()
        finally: conn.close()
        return [self._price_dict(row) for row in rows]

    def save_price(self, *, work_id: str, provider_name: str, model_name: str, enabled: bool, input_price: Decimal, output_price: Decimal, currency: str, expected_revision: int | None, user_id: str, idempotency_key: str, inherit_global: bool = False) -> dict[str, object]:
        request_data={"kind":"price","work_id":work_id,"provider_name":provider_name,"model_name":model_name,"enabled":enabled,"input_price":_money(input_price),"output_price":_money(output_price),"currency":currency,"expected_revision":expected_revision}
        replay, mutation = self._prepare_mutation(idempotency_key,user_id,request_data)
        if replay is not None: return replay
        conn = connect(self._database_path)
        try:
            initialize_schema(conn)
            current = conn.execute("SELECT revision,policy_id FROM model_price_policies WHERE work_id=? AND provider_name=? AND model_name=?", (work_id,provider_name,model_name)).fetchone()
            if current and expected_revision is not None and int(current[0]) != expected_revision: raise ValueError("P2_PRICE_CONFLICT")
            revision = int(current[0]) + 1 if current else 1; policy_id = str(current[1]) if current else f"price_{uuid.uuid4().hex}"
            now = datetime.now(UTC).isoformat()
            conn.execute(
                "INSERT INTO model_price_policies(policy_id,work_id,provider_name,model_name,enabled,inherit_global,input_price_per_1m,output_price_per_1m,currency,revision,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(work_id,provider_name,model_name) DO UPDATE SET enabled=excluded.enabled,inherit_global=excluded.inherit_global,input_price_per_1m=excluded.input_price_per_1m,output_price_per_1m=excluded.output_price_per_1m,currency=excluded.currency,revision=excluded.revision,updated_at=excluded.updated_at",
                (policy_id,work_id,provider_name,model_name,int(enabled),int(bool(inherit_global and work_id)),_money(input_price),_money(output_price),currency,revision,now),
            )
            row = conn.execute("SELECT * FROM model_price_policies WHERE work_id=? AND provider_name=? AND model_name=?", (work_id,provider_name,model_name)).fetchone()
            result=self._price_dict(row)
            self._insert_pending_receipt(conn,mutation,result)
            conn.commit()
        finally: conn.close()
        self._complete_mutation(mutation,result)
        return result

    def resolve_price(self, work_id: str, provider_name: str, model_name: str) -> dict[str, object] | None:
        items = self.list_prices(work_id, provider_name, model_name)
        if items and not items[0].get("inherit_global"): return items[0] if items[0]["enabled"] else None
        globals_ = self.list_prices("", provider_name, model_name)
        return globals_[0] if globals_ and globals_[0]["enabled"] else None

    def get_auto_queue_budget(self, work_id: str) -> dict[str, object] | None:
        conn=connect(self._database_path)
        try:
            initialize_schema(conn); row=conn.execute("SELECT budget_limit_tokens,stop_on_budget_exceeded,revision,updated_at FROM auto_queue_configs WHERE work_id=?",(work_id,)).fetchone()
        finally: conn.close()
        return {"budget_type":"auto_queue","enabled":bool(row[1]) and int(row[0] or 0)>0,"limit":str(int(row[0] or 0)),"currency":"","alert_threshold":"0.800000","revision":int(row[2] or 1),"updated_at":row[3]} if row else None

    def save_auto_queue_budget(self, *, work_id: str, enabled: bool, limit_tokens: int, expected_revision: int | None, user_id: str, idempotency_key: str) -> dict[str, object]:
        request_data={"kind":"auto_queue_budget","work_id":work_id,"enabled":enabled,"limit_tokens":limit_tokens,"expected_revision":expected_revision}; replay,mutation=self._prepare_mutation(idempotency_key,user_id,request_data)
        if replay is not None: return replay
        conn=connect(self._database_path)
        try:
            initialize_schema(conn); row=conn.execute("SELECT revision FROM auto_queue_configs WHERE work_id=?",(work_id,)).fetchone()
            if not row: raise ValueError("P2_BUDGET_NOT_FOUND")
            revision=int(row[0] or 1)
            if expected_revision is not None and revision!=expected_revision: raise ValueError("P2_BUDGET_CONFLICT")
            now=datetime.now(UTC).isoformat(); cursor=conn.execute("UPDATE auto_queue_configs SET budget_limit_tokens=?,stop_on_budget_exceeded=?,revision=?,updated_at=? WHERE work_id=? AND revision=?",(limit_tokens if enabled else 0,int(enabled),revision+1,now,work_id,revision))
            if cursor.rowcount!=1: raise ValueError("P2_BUDGET_CONFLICT")
            result={"budget_type":"auto_queue","enabled":enabled,"limit":str(limit_tokens if enabled else 0),"currency":"","alert_threshold":"0.800000","revision":revision+1,"updated_at":now}; self._insert_pending_receipt(conn,mutation,result); conn.commit()
        finally: conn.close()
        self._complete_mutation(mutation,result); return result

    def get_trend(self, work_id: str, date_from: str, date_to: str) -> list[dict[str, object]]:
        start = date.fromisoformat(date_from); end = date.fromisoformat(date_to)
        if end < start or (end - start).days > 366: raise ValueError("P2_COST_QUERY_INVALID")
        tz = ZoneInfo("Asia/Shanghai"); start_utc = datetime.combine(start, datetime.min.time(), tzinfo=tz).astimezone(UTC).isoformat(); end_utc = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz).astimezone(UTC).isoformat()
        conn = connect(self._database_path)
        try:
            initialize_schema(conn); rows = conn.execute("SELECT started_at,total_tokens,estimated_cost_text,cost_status FROM llm_call_logs WHERE work_id=? AND started_at>=? AND started_at<?", (work_id,start_utc,end_utc)).fetchall()
        finally: conn.close()
        buckets = {}; current = start
        while current <= end: buckets[current.isoformat()] = {"date":current.isoformat(),"call_count":0,"total_tokens":0,"estimated_cost":"0.000000","cost_completeness":"empty"}; current += timedelta(days=1)
        for row in rows:
            day = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00")).astimezone(tz).date().isoformat(); item = buckets[day]; item["call_count"] += 1; item["total_tokens"] += int(row[1] or 0)
            if row[3] == "known" and item["cost_completeness"] != "unknown": item["estimated_cost"] = _money(Decimal(item["estimated_cost"]) + Decimal(str(row[2] or "0"))); item["cost_completeness"] = "known"
            else: item["estimated_cost"] = None; item["cost_completeness"] = "unknown"
        return list(buckets.values())

    def get_task_cost(self, work_id: str, scope_type: str, scope_id: str) -> dict[str, object]:
        if scope_type not in {"job_id","session_id","run_id"}: raise ValueError("P2_COST_SCOPE_INVALID")
        conn = connect(self._database_path)
        try:
            initialize_schema(conn); rows = conn.execute(f"SELECT total_tokens,estimated_cost_text,cost_status,cost_currency,usage_status FROM llm_call_logs WHERE work_id=? AND {scope_type}=?", (work_id,scope_id)).fetchall()
        finally: conn.close()
        unknown = any(row[2] != "known" for row in rows); currencies = {row[3] for row in rows if row[3]}
        usage_unknown=any(row[4]!="known" for row in rows)
        return {"call_count":len(rows),"total_tokens":sum(int(row[0] or 0) for row in rows),"estimated_cost":None if unknown else _money(sum((Decimal(str(row[1] or "0")) for row in rows), Decimal("0"))),"currency":next(iter(currencies)) if len(currencies)==1 and not unknown else None,"cost_completeness":"unknown" if unknown else "complete" if rows else "empty","usage_completeness":"unknown" if usage_unknown else "complete" if rows else "empty"}

    def reconcile_usage(self, work_id: str) -> dict[str, object]:
        inserted = conflicts = 0
        if not self._file_path_for_logs().exists(): return {"resolved":True,"inserted_count":0,"conflict_count":0,"remaining_unknown_count":self._unknown_count(work_id)}
        store = FileLLMCallLogStore(self._file_path_for_logs(), database_path=self._database_path)
        for line in self._file_path_for_logs().read_text(encoding="utf-8").splitlines():
            try:
                entry = LLMCallLog.model_validate_json(line)
                if entry.work_id != work_id: continue
                before = self._request_exists(entry.request_id); store.append(entry); inserted += 0 if before else 1
            except (ValueError, TypeError): conflicts += 1
        remaining = self._unknown_count(work_id)
        return {"resolved":remaining == 0 and conflicts == 0,"inserted_count":inserted,"conflict_count":conflicts,"remaining_unknown_count":remaining}

    def _request_exists(self, request_id: str) -> bool:
        conn=connect(self._database_path)
        try: initialize_schema(conn); return conn.execute("SELECT 1 FROM llm_call_logs WHERE request_id=?",(request_id,)).fetchone() is not None
        finally: conn.close()

    def _unknown_count(self, work_id: str) -> int:
        conn=connect(self._database_path)
        try: initialize_schema(conn); return int(conn.execute("SELECT COUNT(*) FROM llm_call_logs WHERE work_id=? AND (usage_status='unknown' OR cost_status='unknown')",(work_id,)).fetchone()[0])
        finally: conn.close()

    def _file_path_for_logs(self) -> Path: return self._database_path.with_name("llm_call_logs.jsonl")

    @staticmethod
    def _hash(value: object) -> str:
        return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")).hexdigest()

    def _prepare_mutation(self,idempotency_key: str,user_id: str,request_data: dict[str,object]):
        key_hash=self._hash(idempotency_key); request_hash=self._hash(request_data)
        conn=connect(self._database_path)
        try:
            initialize_schema(conn); row=conn.execute("SELECT receipt_id,request_hash,response_json,audit_status FROM cost_control_receipts WHERE key_hash=?",(key_hash,)).fetchone()
            if row:
                if row[1]!=request_hash: raise ValueError("idempotency_conflict")
                result=json.loads(row[2])
                if row[3]!="completed": self._complete_mutation({"receipt_id":row[0],"request_hash":request_hash,"key_hash":key_hash,"user_hash":self._hash(user_id),"resource_hash":self._hash({"work_id":request_data.get("work_id"),"kind":request_data.get("kind")})},result)
                return result,None
            mutation={"receipt_id":f"ccr_{uuid.uuid4().hex}","request_hash":request_hash,"key_hash":key_hash,"user_hash":self._hash(user_id),"resource_hash":self._hash({"work_id":request_data.get("work_id"),"kind":request_data.get("kind")})}
            now=datetime.now(UTC).isoformat(); conn.execute("INSERT INTO cost_control_audits(event_ref,event_key,event_stage,user_id_hash,resource_hash,new_value_hash,created_at) VALUES(?,?,?,?,?,?,?)",(f"audit_{uuid.uuid4().hex}",f"{mutation['receipt_id']}:pre","pre",mutation["user_hash"],mutation["resource_hash"],request_hash,now)); conn.commit()
            return None,mutation
        finally: conn.close()

    @staticmethod
    def _insert_pending_receipt(conn,mutation: dict[str,str],result: dict[str,object]) -> None:
        now=datetime.now(UTC).isoformat(); conn.execute("INSERT INTO cost_control_receipts(receipt_id,key_hash,request_hash,response_json,audit_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(mutation["receipt_id"],mutation["key_hash"],mutation["request_hash"],json.dumps(result,ensure_ascii=False,sort_keys=True),"completion_pending",now,now))

    def _complete_mutation(self,mutation: dict[str,str],result: dict[str,object]) -> None:
        conn=connect(self._database_path)
        try:
            initialize_schema(conn); now=datetime.now(UTC).isoformat(); event_ref=f"audit_{hashlib.sha256((mutation['receipt_id']+':post').encode()).hexdigest()[:24]}"; conn.execute("INSERT OR IGNORE INTO cost_control_audits(event_ref,event_key,event_stage,user_id_hash,resource_hash,new_value_hash,created_at) VALUES(?,?,?,?,?,?,?)",(event_ref,f"{mutation['receipt_id']}:post","post",mutation["user_hash"],mutation["resource_hash"],self._hash(result),now)); conn.execute("UPDATE cost_control_receipts SET audit_status='completed',post_event_ref=?,updated_at=? WHERE receipt_id=?",(event_ref,now,mutation["receipt_id"])); conn.commit()
        finally: conn.close()

    @staticmethod
    def _month_bounds(month: str) -> tuple[str,str]:
        start = datetime.strptime(month, "%Y-%m").replace(day=1,tzinfo=ZoneInfo("Asia/Shanghai")); end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
        return start.astimezone(UTC).isoformat(), end.astimezone(UTC).isoformat()

    @staticmethod
    def _single_currency(rows) -> str | None:
        currencies = set()
        for row in rows:
            value = row[4]
            if value: currencies.add(str(value).upper())
        return next(iter(currencies)) if len(currencies) == 1 else None

    @staticmethod
    def _budget_dict(row) -> dict[str, object]:
        return {"budget_type": row[2], "enabled": bool(row[3]), "inherit_global": bool(row[4]), "limit": row[5], "currency": row[6], "alert_threshold": row[7], "revision": row[8], "updated_at": row[9]}

    @staticmethod
    def _price_dict(row) -> dict[str, object]:
        return {"provider_name":row[2],"model_name":row[3],"enabled":bool(row[4]),"inherit_global":bool(row[5]),"input_price_per_1m":row[6],"output_price_per_1m":row[7],"currency":row[8],"revision":row[9],"updated_at":row[10]}
