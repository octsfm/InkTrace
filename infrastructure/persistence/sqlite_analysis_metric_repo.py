from __future__ import annotations
import json
from datetime import UTC,datetime
from pathlib import Path
from domain.repositories.ai.analysis_metric_repository import AnalysisMetricRepository
from infrastructure.database.models import initialize_schema
from infrastructure.database.session import get_database_path
from infrastructure.database.v1 import connect


class SQLiteAnalysisMetricRepository(AnalysisMetricRepository):
    def __init__(self,database_path: Path|str|None=None): self._database_path=Path(database_path).resolve() if database_path else get_database_path()
    def get(self,work_id,metric_type):
        conn=connect(self._database_path)
        try: initialize_schema(conn); row=conn.execute("SELECT payload_json,source_fingerprint,status,error_code,computed_at,stale FROM analysis_metrics WHERE work_id=? AND metric_type=?",(work_id,metric_type)).fetchone()
        finally: conn.close()
        return {"data":json.loads(row[0]),"source_fingerprint":row[1],"status":row[2],"error_code":row[3],"computed_at":row[4],"stale":bool(row[5])} if row else None
    def save(self,work_id,metric_type,payload,source_fingerprint,status="ready",error_code=""):
        now=datetime.now(UTC).isoformat(); conn=connect(self._database_path)
        try:
            initialize_schema(conn); conn.execute("INSERT INTO analysis_metrics(work_id,metric_type,payload_json,source_fingerprint,status,error_code,computed_at,stale) VALUES(?,?,?,?,?,?,?,0) ON CONFLICT(work_id,metric_type) DO UPDATE SET payload_json=excluded.payload_json,source_fingerprint=excluded.source_fingerprint,status=excluded.status,error_code=excluded.error_code,computed_at=excluded.computed_at,stale=0",(work_id,metric_type,json.dumps(payload,ensure_ascii=False),source_fingerprint,status,error_code,now)); conn.commit()
        finally: conn.close()
        return {"data":payload,"source_fingerprint":source_fingerprint,"status":status,"error_code":error_code,"computed_at":now,"stale":False}
    def status(self,work_id):
        conn=connect(self._database_path)
        try: initialize_schema(conn); rows=conn.execute("SELECT metric_type,status,error_code,computed_at,stale FROM analysis_metrics WHERE work_id=? ORDER BY metric_type",(work_id,)).fetchall()
        finally: conn.close()
        return {"work_status":"failed" if any(row[1]=="failed" for row in rows) else "stale" if any(bool(row[4]) for row in rows) else "ready" if len(rows)>=6 else "missing","metrics":[{"metric_type":row[0],"status":row[1],"error_code":row[2],"computed_at":row[3],"stale":bool(row[4])} for row in rows]}
    def mark_stale(self,work_id,metric_types=None):
        conn=connect(self._database_path)
        try:
            initialize_schema(conn)
            if metric_types:
                placeholders=",".join("?" for _ in metric_types); conn.execute(f"UPDATE analysis_metrics SET stale=1 WHERE work_id=? AND metric_type IN ({placeholders})",(work_id,*metric_types))
            else: conn.execute("UPDATE analysis_metrics SET stale=1 WHERE work_id=?",(work_id,))
            conn.commit()
        finally: conn.close()
