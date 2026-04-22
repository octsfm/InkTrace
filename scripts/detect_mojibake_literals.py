from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

ALLOWED_EXTENSIONS = {".py", ".js", ".vue"}
DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    "logs",
    ".pytest_cache",
    "tests",
}

MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â€",
    "�",
    "瑙",
    "锛",
    "缁",
    "閸",
    "绔",
    "妭",
    "鍒",
    "辫",
    "璇",
    "湇",
    "鍔",
)


def _is_probably_garbled(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    marker_hits = sum(1 for token in MOJIBAKE_MARKERS if token in text)
    if marker_hits >= 2 and len(text) >= 6:
        return True
    if any(token in text for token in ("Ã", "Â", "â€", "�")) and len(text) >= 4:
        return True
    question_count = text.count("?") + text.count("？")
    if question_count >= max(4, len(text) // 5):
        return True
    return False


def _iter_files(roots: Sequence[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file():
            if root.suffix in ALLOWED_EXTENSIONS:
                yield root
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in ALLOWED_EXTENSIONS:
                continue
            parts = set(path.parts)
            if parts & DEFAULT_EXCLUDES:
                continue
            yield path


def _scan_python(path: Path) -> List[Tuple[int, str]]:
    findings: List[Tuple[int, str]] = []
    source = path.read_text(encoding="utf-8", errors="replace")
    reader = io.StringIO(source).readline
    for token in tokenize.generate_tokens(reader):
        if token.type != tokenize.STRING:
            continue
        literal = token.string
        try:
            decoded = ast.literal_eval(literal)
        except Exception:
            decoded = None
        if isinstance(decoded, str) and decoded in MOJIBAKE_MARKERS:
            continue
        if _is_probably_garbled(literal):
            findings.append((token.start[0], literal[:120]))
    return findings


def _scan_js_like(path: Path) -> List[Tuple[int, str]]:
    findings: List[Tuple[int, str]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"""(['"])(?:\\.|(?!\1).)*\1""")
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in pattern.finditer(line):
            literal = match.group(0)
            inner = literal[1:-1] if len(literal) >= 2 else literal
            if inner in MOJIBAKE_MARKERS:
                continue
            if _is_probably_garbled(literal):
                findings.append((line_no, literal[:120]))
    return findings


def scan_paths(paths: Sequence[Path]) -> List[Tuple[Path, int, str]]:
    all_findings: List[Tuple[Path, int, str]] = []
    for file_path in _iter_files(paths):
        if file_path.suffix == ".py":
            findings = _scan_python(file_path)
        else:
            findings = _scan_js_like(file_path)
        for line_no, literal in findings:
            all_findings.append((file_path, line_no, literal))
    return all_findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect likely mojibake literals in source files.")
    parser.add_argument("paths", nargs="*", default=["."], help="Paths to scan")
    args = parser.parse_args(argv)

    roots = [Path(item).resolve() for item in args.paths]
    findings = scan_paths(roots)
    if not findings:
        print("No mojibake literals found.")
        return 0

    print("Potential mojibake literals detected:")
    for file_path, line_no, literal in findings:
        print(f"{file_path}:{line_no}: {literal}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
