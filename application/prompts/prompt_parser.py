from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


def strip_code_fence(text: str) -> str:
    content = str(text or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
        content = re.sub(r"\s*```$", "", content).strip()
    return content


def _candidate_json_strings(text: str) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    candidates = [raw, strip_code_fence(raw)]
    candidates.extend(re.findall(r"```json\s*([\s\S]*?)```", raw, flags=re.IGNORECASE))
    candidates.extend(re.findall(r"```\s*([\s\S]*?)```", raw, flags=re.IGNORECASE))
    candidates.extend(_extract_balanced_json_objects(raw))
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start:end + 1])
    return [str(item).strip() for item in candidates if str(item).strip()]


def _extract_balanced_json_objects(text: str) -> List[str]:
    raw = str(text or "")
    if not raw:
        return []
    results: List[str] = []
    start = -1
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(raw):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == "\"":
                in_string = False
            continue
        if char == "\"":
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
            continue
        if char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    results.append(raw[start:index + 1])
                    start = -1
    return results


def repair_json_string(text: str) -> str:
    content = str(text or "").strip()
    if not content:
        return ""
    content = content.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", content)
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    return content


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    for item in _candidate_json_strings(text):
        for candidate in (item, repair_json_string(item)):
            try:
                value = json.loads(candidate)
                if isinstance(value, dict):
                    return value
            except Exception:
                continue
    return None


def parse_json_array(text: str) -> List[Dict[str, Any]]:
    raw = str(text or "").strip()
    candidates = [raw, strip_code_fence(raw)]
    start = raw.find("[")
    end = raw.rfind("]")
    if start >= 0 and end > start:
        candidates.append(raw[start:end + 1])
    for item in candidates:
        for candidate in (item, repair_json_string(item)):
            try:
                value = json.loads(candidate)
                if isinstance(value, list):
                    return [entry for entry in value if isinstance(entry, dict)]
            except Exception:
                continue
    return []
