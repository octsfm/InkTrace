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
        self._world_settings: List[str] = []
        self._plot_threads: Dict[str, PlotThreadMemory] = {}
        self._style_profile = StyleProfileMemory()

    def merge_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        self._merge_characters(analysis.get("characters") or [])
        self._merge_world_settings(analysis.get("world_settings") or [])
        self._merge_plot_threads(
            analysis.get("plot_outline")
            or analysis.get("plot_threads")
            or analysis.get("plot_points")
            or []
        )
        self._style_profile.merge(analysis.get("writing_style") or analysis.get("style_profile") or {})
        return self.to_agent_context()

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
        text = str(value).strip()
        if text and text not in self._world_settings:
            self._world_settings.append(text)
        return self.to_agent_context()

    def to_agent_context(self) -> Dict[str, Any]:
        plot_outline = []
        for thread in sorted(self._plot_threads.values(), key=lambda p: p.title):
            if thread.points:
                plot_outline.append(f"{thread.title}：{thread.points[-1]}")
            else:
                plot_outline.append(thread.title)
        return {
            "characters": [
                {
                    "name": char.name,
                    "traits": list(char.traits),
                    "relationships": dict(char.relationships)
                }
                for char in sorted(self._characters.values(), key=lambda c: c.name)
            ],
            "world_settings": list(self._world_settings),
            "plot_outline": plot_outline,
            "plot_threads": [
                {
                    "title": thread.title,
                    "points": list(thread.points),
                    "status": thread.status
                }
                for thread in sorted(self._plot_threads.values(), key=lambda p: p.title)
            ],
            "writing_style": {
                "tone": self._style_profile.tone,
                "pacing": self._style_profile.pacing,
                "narrative_style": self._style_profile.narrative_style
            },
            "style_profile": {
                "tone": self._style_profile.tone,
                "pacing": self._style_profile.pacing,
                "narrative_style": self._style_profile.narrative_style
            },
            "current_progress": {
                "latest_chapter_number": 0,
                "latest_goal": "",
                "last_summary": ""
            }
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
            if text and text not in self._world_settings:
                self._world_settings.append(text)

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
                    by_name[name]["relationships"][target_name] = relation_text

    def _listify(value: Any) -> List[str]:
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    world_settings = list(dict.fromkeys([*_listify(base.get("world_settings")), *_listify(incoming.get("world_settings"))]))
    plot_outline = list(dict.fromkeys([*_listify(base.get("plot_outline")), *_listify(incoming.get("plot_outline"))]))

    base_style = base.get("writing_style") or base.get("style_profile") or {}
    incoming_style = incoming.get("writing_style") or incoming.get("style_profile") or {}
    writing_style = {
        "tone": str(incoming_style.get("tone") or base_style.get("tone") or "").strip(),
        "pacing": str(incoming_style.get("pacing") or base_style.get("pacing") or "").strip(),
        "narrative_style": str(
            incoming_style.get("narrative_style")
            or base_style.get("narrative_style")
            or ""
        ).strip()
    }
    current_progress = incoming.get("current_progress") or base.get("current_progress") or {
        "latest_chapter_number": 0,
        "latest_goal": "",
        "last_summary": ""
    }

    merged = {
        "characters": list(by_name.values()),
        "world_settings": world_settings,
        "plot_outline": plot_outline,
        "writing_style": writing_style,
        "current_progress": current_progress
    }
    merged["style_profile"] = dict(writing_style)
    return merged
