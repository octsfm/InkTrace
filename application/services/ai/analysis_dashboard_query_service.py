from __future__ import annotations

from datetime import UTC, datetime
import json
import re

from application.services.ai.analysis_dashboard_constants import AI_SIGNAL_WORDS, CLIFFHANGER_WORDS, STOP_WORDS_ZH
from domain.services.ai.text_analysis import NovelTextAnalyzer


def _enum_value(value) -> str:
    return str(getattr(value, "value", value) or "")


class AnalysisDashboardQueryService:
    def __init__(
        self,
        *,
        chapter_repository,
        candidate_draft_repository,
        style_profile_repository=None,
        writing_asset_service=None,
        plot_arc_repository=None,
        **_unused,
    ) -> None:
        self._chapters = chapter_repository
        self._candidates = candidate_draft_repository
        self._styles = style_profile_repository
        self._assets = writing_asset_service
        self._plot_arcs = plot_arc_repository
        self._analyzer = NovelTextAnalyzer()

    def source_fingerprint_parts(self, work_id: str) -> list[str]:
        parts=[]
        for item in self._candidates.list_by_work(work_id):
            parts.append(f"candidate:{getattr(item,'candidate_draft_id','')}:{_enum_value(getattr(item,'status',''))}:{getattr(item,'updated_at','')}:{getattr(item,'applied_at','')}")
        active=self._styles.get_active(work_id) if self._styles else None
        if active: parts.append(f"style:{getattr(active,'profile_id','')}:{getattr(active,'version',0)}:{getattr(active,'updated_at','')}:{_enum_value(getattr(active,'status',''))}")
        if self._plot_arcs:
            for item in self._plot_arcs.list_sequence_arcs(work_id): parts.append(f"sequence:{item.sequence_arc_id}:{item.version}:{item.updated_at}")
        return parts

    def _confirmed_chapters(self, work_id: str):
        # 当前 V1.1 没有独立 confirmed_at；持久化 Chapter.content 即正式正文。
        return [item for item in self._chapters.list_by_work(work_id) if str(getattr(item, "content", "")).strip()]

    def _candidate_stats(self, work_id: str) -> tuple[list, list]:
        items = list(self._candidates.list_by_work(work_id))
        adopted = [item for item in items if _enum_value(getattr(item, "status", "")) == "applied" or getattr(item, "applied_at", "")]
        return items, adopted

    async def get_writing_stats(self, work_id: str) -> dict[str, object]:
        chapters = self._confirmed_chapters(work_id)
        candidates, adopted = self._candidate_stats(work_id)
        counts = [self._analyzer.effective_length(item.content) for item in chapters]
        dates = [getattr(item, "created_at", None) for item in chapters if getattr(item, "created_at", None)]
        active_days = max(1, ((max(dates) - min(dates)).days + 1) if dates else 1)
        total = sum(counts)
        return {
            "total_word_count": total,
            "daily_avg_words": round(total / active_days, 1) if total else 0.0,
            "chapter_word_counts": [
                {
                    "chapter_id": str(getattr(item.id, "value", item.id)),
                    "chapter_index": int(getattr(item, "order_index", index + 1)),
                    "title": item.title,
                    "word_count": counts[index],
                }
                for index, item in enumerate(chapters)
            ],
            "ai_adoption_rate": round(len(adopted) / len(candidates), 4) if candidates else 0.0,
            "total_chapters": len(chapters),
            "active_days": active_days if chapters else 0,
        }

    async def get_rhythm_analysis(self, work_id: str) -> dict[str, object]:
        chapters = self._confirmed_chapters(work_id)
        counts = [self._analyzer.effective_length(item.content) for item in chapters]
        features = [self._analyzer.features(item.content) for item in chapters]
        cliffhangers = []
        for item in chapters:
            sentences = self._analyzer.sentences(item.content)[-3:]
            tail = "".join(sentences)
            cliffhangers.append({
                "chapter_id": str(getattr(item.id, "value", item.id)),
                "question_count": sum(1 for sentence in sentences if sentence.endswith(("？", "?"))),
                "conflict_word_count": sum(tail.count(word) for word in CLIFFHANGER_WORDS),
            })
        climax_chapters=[]
        if self._plot_arcs:
            for arc in self._plot_arcs.list_sequence_arcs(work_id):
                climax_chapters.extend(int(event.estimated_chapter) for event in arc.key_events if str(event.event_type).lower()=="climax" and int(event.estimated_chapter or 0)>0)
        climax_chapters=sorted(set(climax_chapters))
        return {
            "chapter_word_count_std": self._analyzer._std(counts),
            "avg_paragraph_length": self._analyzer._mean([value["avg_paragraph_length"] for value in features]),
            "paragraph_length_std": self._analyzer._mean([value["paragraph_length_std"] for value in features]),
            "dialogue_ratio_trend": [value["dialogue_ratio"] for value in features],
            "short_sentence_density": self._analyzer._mean([value["short_sentence_ratio"] for value in features]),
            "cliffhanger_stats": {"per_chapter": cliffhangers},
            "climax_intervals": [{"from_chapter":left,"to_chapter":right,"interval":right-left} for left,right in zip(climax_chapters,climax_chapters[1:])],
        }

    async def get_dialogue_analysis(self, work_id: str) -> dict[str, object]:
        chapters = self._confirmed_chapters(work_id)
        text = "\n\n".join(item.content for item in chapters)
        segments = self._analyzer.dialogue_segments(text)
        total = max(self._analyzer.effective_length(text), 1)
        dialogue_chars = sum(self._analyzer.effective_length(item) for item in segments)
        by_character={}
        attributed_chars=0
        if self._assets:
            names={}
            for item in self._assets.list_characters(work_id, ""):
                names[str(item.name)]=str(item.name)
                try:
                    for alias in json.loads(str(getattr(item,"aliases_json","[]") or "[]")): names[str(alias)]=str(item.name)
                except (TypeError,json.JSONDecodeError): pass
            for chapter in chapters:
                chapter_seen=set()
                for match in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9_]{1,20}?)(?:说|道|问|答)?[：:]\s*[“「『\"]([^”」』\"]+)[”」』\"]",chapter.content):
                    speaker=names.get(match.group(1)); chars=self._analyzer.effective_length(match.group(2))
                    if not speaker: continue
                    entry=by_character.setdefault(speaker,{"dialogue_chars":0,"dialogue_ratio":0.0,"chapter_count":0}); entry["dialogue_chars"]+=chars; attributed_chars+=chars
                    if speaker not in chapter_seen: entry["chapter_count"]+=1; chapter_seen.add(speaker)
        for entry in by_character.values(): entry["dialogue_ratio"]=round(entry["dialogue_chars"]/max(dialogue_chars,1),4)
        return {
            "dialogue_ratio": round(dialogue_chars / total, 4) if chapters else 0.0,
            "avg_dialogue_length": self._analyzer._mean([self._analyzer.effective_length(item) for item in segments]),
            "by_character": by_character,
            "unknown_ratio": round(max(dialogue_chars-attributed_chars,0)/max(dialogue_chars,1),4) if segments else 0.0,
            "note": "角色归因为启发式匹配，可能存在误差，仅供参考",
        }

    async def get_word_frequency(self, work_id: str, *, top_n: int = 50) -> dict[str, object]:
        chapters = self._confirmed_chapters(work_id)
        tokens = self._analyzer.word_tokens("\n".join(item.content for item in chapters))
        filtered = self._analyzer.top_words(tokens, STOP_WORDS_ZH, max(10, min(int(top_n), 200)))
        total_docs = max(len(chapters), 1)
        words = []
        for word, frequency in filtered:
            document_count = sum(1 for item in chapters if word in item.content)
            tfidf = frequency * (1.0 if not document_count else total_docs / document_count)
            words.append({"word": word, "frequency": frequency, "tfidf_score": round(tfidf, 4)})
        return {"words": words, "total_unique_words": len(set(tokens)), "stop_words_removed": max(0, len(tokens) - sum(value for _, value in filtered))}

    async def get_style_consistency(self, work_id: str) -> dict[str, object]:
        chapters = self._confirmed_chapters(work_id)
        if not chapters:
            return {"drift_index": 0.0, "consistency_score": 0.0, "chapter_trend": [], "baseline_source": "chapter_mean", "warning": "no_confirmed_chapters"}
        features = [self._analyzer.features(item.content) for item in chapters]
        active = self._styles.get_active(work_id) if self._styles else None
        keys = ("avg_sentence_length", "dialogue_ratio", "short_sentence_ratio", "long_sentence_ratio", "avg_paragraph_length")
        if active:
            baseline = {key: float(getattr(active, key, 0.0) or 0.0) for key in keys}
            source, warning = "style_profile", None
        else:
            baseline = {key: self._analyzer._mean([item[key] for item in features]) for key in keys}
            source, warning = "chapter_mean", "no_active_style_profile"
        trend = []
        deviations = []
        for chapter, values in zip(chapters, features):
            normalized = [abs(values[key] - baseline[key]) / max(abs(baseline[key]), 1.0) for key in keys]
            deviation = min(1.0, self._analyzer._mean(normalized))
            deviations.append(deviation)
            trend.append({
                "chapter_id": str(getattr(chapter.id, "value", chapter.id)),
                "chapter_index": int(getattr(chapter, "order_index", 0)),
                "avg_sentence_length": values["avg_sentence_length"],
                "dialogue_ratio": values["dialogue_ratio"],
                "deviation_from_baseline": deviation,
            })
        drift = min(1.0, self._analyzer._mean(deviations))
        return {"drift_index": drift, "consistency_score": round(1 - drift, 4), "chapter_trend": trend, "baseline_source": source, "warning": warning}

    async def get_ai_usage_analysis(self, work_id: str) -> dict[str, object]:
        chapters = self._confirmed_chapters(work_id)
        candidates, adopted = self._candidate_stats(work_id)
        revision_counts = [int(getattr(item, "revision_count", 0) or 0) for item in candidates]
        full_text = "\n".join(item.content for item in chapters)
        signals = [
            {"word": word, "chapter_count": sum(1 for item in chapters if word in item.content), "total_occurrences": full_text.count(word)}
            for word in sorted(AI_SIGNAL_WORDS)
            if word in full_text
        ]
        return {
            "adoption_rate": round(len(adopted) / len(candidates), 4) if candidates else 0.0,
            "avg_revision_rounds": self._analyzer._mean(revision_counts),
            "ai_word_frequency": signals,
            "total_candidates": len(candidates),
            "total_adopted": len(adopted),
            "disclaimer": "AI 常见词汇仅统计出现频率，不代表文本一定由 AI 生成",
            "computed_at": datetime.now(UTC).isoformat(),
        }
