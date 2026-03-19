from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CharacterMemory:
    name: str
    traits: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)

    def merge(self, payload: Dict[str, Any]) -> None:
        for trait in payload.get("traits") or []:
            text = str(trait).strip()
            if text and text not in self.traits:
                self.traits.append(text)
        relationships = payload.get("relationships") or {}
        if isinstance(relationships, dict):
            for target, relation in relationships.items():
                target_name = str(target).strip()
                relation_text = str(relation).strip()
                if target_name and relation_text:
                    self.relationships[target_name] = relation_text


@dataclass
class PlotThreadMemory:
    title: str
    points: List[str] = field(default_factory=list)
    status: str = "ongoing"

    def merge(self, payload: Dict[str, Any]) -> None:
        for key in ("description", "point", "summary"):
            value = str(payload.get(key) or "").strip()
            if value and value not in self.points:
                self.points.append(value)
        status = str(payload.get("status") or "").strip()
        if status:
            self.status = status


@dataclass
class StyleProfileMemory:
    tone: str = ""
    pacing: str = ""
    narrative_style: str = ""

    def merge(self, payload: Dict[str, Any]) -> None:
        tone = str(payload.get("tone") or "").strip()
        pacing = str(payload.get("pacing") or "").strip()
        narrative_style = str(payload.get("narrative_style") or "").strip()
        if tone:
            self.tone = tone
        if pacing:
            self.pacing = pacing
        if narrative_style:
            self.narrative_style = narrative_style


class NovelMemory:
    def __init__(self) -> None:
        self._characters: Dict[str, CharacterMemory] = {}
        self._world_settings: str = ""
        self._plot_threads: Dict[str, PlotThreadMemory] = {}
        self._style_profile_text: str = ""
        self._current_progress_text: str = ""
        self._events: List[Dict[str, Any]] = []

    def merge_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        merged = merge_memory(self.to_agent_context(), analysis)
        self._characters = {}
        for item in merged.get("characters") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            cm = CharacterMemory(name=name)
            cm.merge(item)
            self._characters[name] = cm
        self._world_settings = str(merged.get("world_settings") or "")
        self._style_profile_text = str(merged.get("writing_style") or "")
        self._current_progress_text = str(merged.get("current_progress") or "")
        self._events = [ev for ev in (merged.get("events") or []) if isinstance(ev, dict)]
        self._plot_threads = {}
        for point in _split_text_points(str(merged.get("plot_outline") or "")):
            self._plot_threads[point] = PlotThreadMemory(title=point, points=[point], status="ongoing")
        return merged

    def update_character_relationship(self, name: str, target: str, relationship: str) -> Dict[str, Any]:
        char_name = str(name).strip()
        target_name = str(target).strip()
        relation_text = str(relationship).strip()
        if not char_name or not target_name or not relation_text:
            return self.to_agent_context()
        if char_name not in self._characters:
            self._characters[char_name] = CharacterMemory(name=char_name)
        self._characters[char_name].relationships[target_name] = relation_text
        return self.to_agent_context()

    def add_world_setting(self, value: str) -> Dict[str, Any]:
        return merge_memory(self.to_agent_context(), {"world_settings": str(value or "")})

    def to_agent_context(self) -> Dict[str, Any]:
        plot_outline = "；".join(
            [thread.points[-1] if thread.points else thread.title for thread in sorted(self._plot_threads.values(), key=lambda p: p.title)]
        ).strip("；")
        return {
            "characters": [
                {
                    "name": char.name,
                    "traits": list(char.traits),
                    "relationships": dict(char.relationships)
                }
                for char in sorted(self._characters.values(), key=lambda c: c.name)
            ],
            "world_settings": self._world_settings,
            "plot_outline": plot_outline,
            "writing_style": self._style_profile_text,
            "current_progress": self._current_progress_text,
            "events": list(self._events)
        }

    def _merge_characters(self, characters: List[Any]) -> None:
        for item in characters:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            if name not in self._characters:
                self._characters[name] = CharacterMemory(name=name)
            self._characters[name].merge(item)

    def _merge_world_settings(self, world_settings: List[Any]) -> None:
        for item in world_settings:
            if isinstance(item, dict):
                text = str(item.get("content") or item.get("description") or item.get("name") or "").strip()
            else:
                text = str(item).strip()
            if text:
                self._world_settings = _concat_unique_text(self._world_settings, text)

    def _merge_plot_threads(self, plot_threads: List[Any]) -> None:
        for item in plot_threads:
            payload: Dict[str, Any]
            if isinstance(item, dict):
                payload = item
                title = str(payload.get("title") or payload.get("name") or "").strip()
            else:
                payload = {"description": str(item)}
                title = str(item).strip()
            if not title:
                continue
            if title not in self._plot_threads:
                self._plot_threads[title] = PlotThreadMemory(title=title)
            self._plot_threads[title].merge(payload)


def merge_memory(old_memory: Dict[str, Any], new_memory: Dict[str, Any]) -> Dict[str, Any]:
    base = old_memory if isinstance(old_memory, dict) else {}
    incoming = new_memory if isinstance(new_memory, dict) else {}

    by_name: Dict[str, Dict[str, Any]] = {}
    for item in base.get("characters") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        by_name[name] = {
            "name": name,
            "traits": [str(v).strip() for v in (item.get("traits") or []) if str(v).strip()],
            "relationships": {
                str(k).strip(): str(v).strip()
                for k, v in (item.get("relationships") or {}).items()
                if str(k).strip() and str(v).strip()
            }
        }
    for item in incoming.get("characters") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if name not in by_name:
            by_name[name] = {"name": name, "traits": [], "relationships": {}}
        traits = [str(v).strip() for v in (item.get("traits") or []) if str(v).strip()]
        by_name[name]["traits"] = list(dict.fromkeys([*by_name[name]["traits"], *traits]))
        rel = item.get("relationships") or {}
        if isinstance(rel, dict):
            for target, relation in rel.items():
                target_name = str(target).strip()
                relation_text = str(relation).strip()
                if target_name and relation_text:
                    if target_name not in by_name[name]["relationships"]:
                        by_name[name]["relationships"][target_name] = relation_text

    world_settings = _concat_unique_text(base.get("world_settings"), incoming.get("world_settings"))
    plot_outline = _concat_unique_text(base.get("plot_outline"), incoming.get("plot_outline"))
    writing_style = _concat_unique_text(base.get("writing_style"), incoming.get("writing_style") or incoming.get("style_profile"))
    current_progress = _concat_unique_text(base.get("current_progress"), incoming.get("current_progress"))
    events = [ev for ev in (base.get("events") or []) if isinstance(ev, dict)]
    incoming_events = [ev for ev in (incoming.get("events") or []) if isinstance(ev, dict)]
    events.extend([_normalize_event(ev) for ev in incoming_events if _normalize_event(ev)])

    merged = {
        "characters": list(by_name.values()),
        "world_settings": world_settings,
        "plot_outline": plot_outline,
        "writing_style": writing_style,
        "current_progress": current_progress,
        "events": events
    }
    return merged


def _split_text_points(value: str) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    segments = re_split_points(text)
    return [s for s in segments if s]


def _concat_unique_text(old_value: Any, new_value: Any) -> str:
    points = []
    for item in _to_text_points(old_value):
        if item not in points:
            points.append(item)
    for item in _to_text_points(new_value):
        if item not in points:
            points.append(item)
    return "；".join(points)


def _to_text_points(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [s for s in re_split_points(value) if s]
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                text = str(item.get("content") or item.get("description") or item.get("name") or item.get("event") or "").strip()
            else:
                text = str(item).strip()
            if not text:
                continue
            for seg in re_split_points(text):
                if seg:
                    items.append(seg)
        return items
    if isinstance(value, dict):
        text = str(value)
        return [s for s in re_split_points(text) if s]
    text = str(value).strip()
    return [s for s in re_split_points(text) if s]


def re_split_points(text: str) -> List[str]:
    normalized = str(text or "").replace("\n", "；")
    parts = []
    for part in normalized.split("；"):
        segment = part.strip().strip("。")
        if segment:
            parts.append(segment)
    return parts


def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "event": str(event.get("event") or "").strip(),
        "actors": [str(v).strip() for v in (event.get("actors") or []) if str(v).strip()],
        "action": str(event.get("action") or "").strip(),
        "result": str(event.get("result") or "").strip(),
        "impact": str(event.get("impact") or "").strip()
    }
    if not payload["event"] or not payload["action"] or not payload["result"] or not payload["impact"]:
        return {}
    return payload
