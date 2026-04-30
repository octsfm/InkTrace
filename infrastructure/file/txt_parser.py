"""
TXT 文件解析器。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional


@dataclass
class ChapterData:
    number: int
    title: str
    content: str
    word_count: int


class TxtParser:
    READ_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030"]

    CHAPTER_PATTERNS = [
        r"^\s*第[零〇一二两三四五六七八九十百千万\d]+章[^\n]*$",
        r"^\s*第[零〇一二两三四五六七八九十百千万\d]+节[^\n]*$",
        r"^\s*chapter\s*\d+[:：\s-]*[^\n]*$",
        r"^\s*\d+[\.、\s-]+[^\n]{1,40}$",
    ]

    SECTION_PATTERNS = [
        r"^[^\n]{1,30}$",
    ]

    def _normalize_newlines(self, content: str) -> str:
        return str(content or "").replace("\r\n", "\n").replace("\r", "\n")

    def _decode_bytes(self, raw_bytes: bytes) -> str:
        last_error: Optional[Exception] = None
        for encoding in self.READ_ENCODINGS:
            try:
                return self._normalize_newlines(raw_bytes.decode(encoding))
            except UnicodeDecodeError as error:
                last_error = error
        if last_error is not None:
            raise last_error
        return self._normalize_newlines(raw_bytes.decode("utf-8"))

    def _read_text(self, filepath: str) -> str:
        return self._decode_bytes(Path(filepath).read_bytes())

    def detect_chapter_pattern_from_content(self, content: str) -> Optional[re.Pattern]:
        for pattern_str in self.CHAPTER_PATTERNS:
            flags = re.MULTILINE | (re.IGNORECASE if "chapter" in pattern_str.lower() else 0)
            matches = re.findall(pattern_str, content, flags)
            if len(matches) >= 1:
                return re.compile(pattern_str, flags)
        return None

    def detect_chapter_pattern(self, filepath: str) -> Optional[re.Pattern]:
        content = self._read_text(filepath)
        return self.detect_chapter_pattern_from_content(content)

    def parse_chapters_from_content(self, content: str) -> List[Dict]:
        pattern = self.detect_chapter_pattern_from_content(content)
        if not pattern:
            return []

        matches = list(pattern.finditer(content))
        chapters: List[Dict] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            title_line = match.group().strip()
            chapter_content = content[start:end].strip()
            number = self._extract_chapter_number(title_line) or (index + 1)
            title = self._extract_chapter_title(title_line)
            chapters.append(
                {
                    "number": number,
                    "title": title,
                    "content": chapter_content,
                    "word_count": self.count_words(chapter_content),
                }
            )
        return chapters

    def parse_chapters(self, filepath: str) -> List[Dict]:
        return self.parse_chapters_from_content(self._read_text(filepath))

    def parse_novel_content(self, content: str) -> Dict:
        pattern = self.detect_chapter_pattern_from_content(content)
        if pattern:
            first_match = pattern.search(content)
            intro = content[: first_match.start()].strip() if first_match else ""
            chapters = self.parse_chapters_from_content(content)
            return {"intro": intro, "chapters": chapters}

        fallback_title = "全本导入"
        fallback_content = content.strip()
        chapters = [
            {
                "number": 1,
                "title": fallback_title,
                "content": fallback_content,
                "word_count": self.count_words(fallback_content),
            }
        ]
        return {"intro": "", "chapters": chapters}

    def parse_uploaded_novel_file(self, raw_bytes: bytes) -> Dict:
        content = self._decode_bytes(raw_bytes)
        return self.parse_novel_content(content)

    def parse_novel_file(self, filepath: str) -> Dict:
        return self.parse_novel_content(self._read_text(filepath))

    def parse_outline_file(self, filepath: str) -> Dict:
        content = self._read_text(filepath)
        result = {
            "genre": "",
            "story_background": "",
            "world_setting": "",
            "target_word_count": "",
            "raw_content": content,
        }

        section_map = {
            "题材": "genre",
            "故事背景": "story_background",
            "背景设定": "story_background",
            "世界背景": "world_setting",
            "世界观": "world_setting",
            "世界设定": "world_setting",
            "预计字数": "target_word_count",
            "目标字数": "target_word_count",
            "字数": "target_word_count",
        }

        lines = [line.strip() for line in content.splitlines()]
        for index, line in enumerate(lines):
            if not line:
                continue
            for key, field in section_map.items():
                if key in line:
                    value = self._extract_outline_value(lines, index, key)
                    if not value:
                        break
                    if field == "target_word_count":
                        numbers = re.findall(r"[\d万]+", value)
                        if numbers:
                            result[field] = numbers[0]
                    else:
                        result[field] = value
                    break

        if not result["story_background"]:
            result["story_background"] = content[:2400]
        if not result["world_setting"]:
            result["world_setting"] = content[:2400]
        return result

    def rebuild_chapters_from_preview(self, chapter_items: List[Dict]) -> Dict:
        chapters: List[Dict] = []
        for index, item in enumerate(chapter_items or [], 1):
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            title = str(item.get("title") or f"第{index}章").strip() or f"第{index}章"
            number = int(item.get("number") or index)
            chapters.append(
                {
                    "number": number,
                    "title": title,
                    "content": content,
                    "word_count": self.count_words(content),
                }
            )
        return {"intro": "", "chapters": chapters}

    def extract_sections(self, content: str) -> List[Dict]:
        sections: List[Dict] = []
        current_title = ""
        current_content: List[str] = []

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if self._is_section_title_candidate(line) and (
                not current_title or self._has_substantive_content(current_content)
            ):
                if current_title:
                    sections.append(
                        {
                            "title": current_title,
                            "content": "\n".join(current_content).strip(),
                        }
                    )
                current_title = line
                current_content = []
            else:
                current_content.append(raw_line)

        if current_title:
            sections.append(
                {
                    "title": current_title,
                    "content": "\n".join(current_content).strip(),
                }
            )
        return [section for section in sections if section["content"]]

    def count_words(self, text: str) -> int:
        cleaned = re.sub(r"\s+", "", text or "")
        return len(cleaned)

    def _extract_chapter_number(self, title_line: str) -> int:
        match = re.search(r"第([零〇一二两三四五六七八九十百千万\d]+)[章节]", title_line, re.IGNORECASE)
        if match:
            return self._parse_number(match.group(1))
        match = re.search(r"chapter\s*(\d+)", title_line, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"^\s*(\d+)", title_line)
        if match:
            return int(match.group(1))
        return 0

    def _extract_chapter_title(self, title_line: str) -> str:
        match = re.search(r"第[零〇一二两三四五六七八九十百千万\d]+[章节]\s*(.+)", title_line, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
        match = re.search(r"chapter\s*\d+[:：\s-]*(.+)", title_line, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
        match = re.search(r"^\s*\d+[\.、\s-]+(.+)", title_line)
        if match and match.group(1).strip():
            return match.group(1).strip()
        return title_line.strip()

    def _extract_outline_value(self, lines: List[str], index: int, key: str) -> str:
        current = lines[index]
        inline = re.split(r"[:：]", current, maxsplit=1)
        if len(inline) == 2 and inline[1].strip():
            return inline[1].strip()
        for next_index in range(index + 1, len(lines)):
            next_line = lines[next_index].strip()
            if not next_line:
                continue
            if any(token in next_line for token in ("题材", "故事背景", "背景设定", "世界背景", "世界观", "世界设定", "预计字数", "目标字数", "字数")):
                break
            return next_line
        return ""

    def _parse_number(self, raw: str) -> int:
        if raw.isdigit():
            return int(raw)

        mapping = {
            "零": 0,
            "〇": 0,
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
        }
        units = {"十": 10, "百": 100, "千": 1000, "万": 10000}

        total = 0
        current = 0
        for char in raw:
            if char in mapping:
                current = mapping[char]
                continue
            if char in units:
                unit = units[char]
                if current == 0:
                    current = 1
                total += current * unit
                current = 0
        return total + current

    def _is_section_title_candidate(self, line: str) -> bool:
        if not line or len(line) > 30:
            return False
        if line.startswith("#"):
            return False
        if re.search(r"[。！？：；，]$", line):
            return False
        return True

    def _has_substantive_content(self, lines: List[str]) -> bool:
        for raw_line in lines:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                return True
        return False
