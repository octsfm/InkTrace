from __future__ import annotations
import asyncio
import hashlib
from datetime import UTC,datetime


class AnalysisMetricService:
    METRICS=("overview","rhythm","dialogue","word_frequency","style","ai_usage")
    def __init__(self,query_service,repository,chapter_repository,large_work_threshold: int=300000): self._query=query_service; self._repo=repository; self._chapters=chapter_repository; self._threshold=large_work_threshold; self._recompute_states={}; self._tasks={}
    def _fingerprint(self,work_id):
        parts=[f"{getattr(item,'id','')}:{getattr(item,'version',0)}:{getattr(item,'updated_at','')}" for item in self._chapters.list_by_work(work_id)]
        if hasattr(self._query,"source_fingerprint_parts"): parts.extend(self._query.source_fingerprint_parts(work_id))
        return hashlib.sha256("|".join(parts).encode()).hexdigest()
    def _large(self,work_id): return sum(len(str(getattr(item,"content","") or "")) for item in self._chapters.list_by_work(work_id))>=self._threshold
    async def _get(self,work_id,metric,compute):
        fingerprint=self._fingerprint(work_id); cached=self._repo.get(work_id,metric)
        if self._large(work_id) and cached and cached["source_fingerprint"]==fingerprint and cached["status"]=="ready": return cached["data"]
        data=await compute(work_id); self._repo.save(work_id,metric,data,fingerprint); return data
    async def get_writing_stats(self,work_id): return await self._get(work_id,"overview",self._query.get_writing_stats)
    async def get_rhythm_analysis(self,work_id): return await self._get(work_id,"rhythm",self._query.get_rhythm_analysis)
    async def get_dialogue_analysis(self,work_id): return await self._get(work_id,"dialogue",self._query.get_dialogue_analysis)
    async def get_word_frequency(self,work_id,top_n=50): return await self._get(work_id,"word_frequency",lambda value:self._query.get_word_frequency(value,top_n=top_n))
    async def get_style_consistency(self,work_id): return await self._get(work_id,"style",self._query.get_style_consistency)
    async def get_ai_usage_analysis(self,work_id): return await self._get(work_id,"ai_usage",self._query.get_ai_usage_analysis)
    async def get_metric_response(self,work_id,metric,top_n=50):
        methods={"overview":self._query.get_writing_stats,"rhythm":self._query.get_rhythm_analysis,"dialogue":self._query.get_dialogue_analysis,"word_frequency":lambda value:self._query.get_word_frequency(value,top_n=top_n),"style":self._query.get_style_consistency,"ai_usage":self._query.get_ai_usage_analysis}
        method=methods[metric]
        if not self._large(work_id):
            return {"source":"realtime","computed_at":datetime.now(UTC).isoformat(),"stale":False,"data":await method(work_id)}
        fingerprint=self._fingerprint(work_id); cached=self._repo.get(work_id,metric)
        if cached is None:
            cached=self._repo.save(work_id,metric,await method(work_id),fingerprint)
        stale=bool(cached.get("stale")) or cached.get("source_fingerprint")!=fingerprint
        if stale and not cached.get("stale"): self._repo.mark_stale(work_id,[metric])
        return {"source":"cached","computed_at":cached.get("computed_at","") or "","stale":stale,"data":cached.get("data",{})}
    async def refresh(self,work_id):
        fingerprint=self._fingerprint(work_id); methods=(self._query.get_writing_stats,self._query.get_rhythm_analysis,self._query.get_dialogue_analysis,lambda value:self._query.get_word_frequency(value,top_n=50),self._query.get_style_consistency,self._query.get_ai_usage_analysis)
        for metric,method in zip(self.METRICS,methods):
            try: self._repo.save(work_id,metric,await method(work_id),fingerprint)
            except Exception as exc: self._repo.save(work_id,metric,{},fingerprint,status="failed",error_code=getattr(exc,"error_code","analysis_refresh_failed")); raise
        return self._repo.status(work_id)
    def status(self,work_id): return self._repo.status(work_id)
    def is_large(self,work_id): return self._large(work_id)
    def recompute_status(self,work_id): return self._recompute_states.get(work_id,{"status":"idle","progress":0.0})
    def start_recompute(self,work_id):
        current=self.recompute_status(work_id)
        if current["status"]=="running": return current
        self._recompute_states[work_id]={"status":"running","progress":0.0}
        self._tasks[work_id]=asyncio.create_task(self._run_recompute(work_id))
        return {"accepted":True,"work_id":work_id,"estimated_seconds":6}
    async def _run_recompute(self,work_id):
        fingerprint=self._fingerprint(work_id); methods=(self._query.get_writing_stats,self._query.get_rhythm_analysis,self._query.get_dialogue_analysis,lambda value:self._query.get_word_frequency(value,top_n=50),self._query.get_style_consistency,self._query.get_ai_usage_analysis)
        try:
            for index,(metric,method) in enumerate(zip(self.METRICS,methods),start=1):
                self._repo.save(work_id,metric,await method(work_id),fingerprint); self._recompute_states[work_id]={"status":"running","progress":index/len(self.METRICS)}
            self._recompute_states[work_id]={"status":"completed","progress":1.0}
        except Exception:
            self._recompute_states[work_id]={"status":"failed","progress":self._recompute_states[work_id].get("progress",0.0)}
