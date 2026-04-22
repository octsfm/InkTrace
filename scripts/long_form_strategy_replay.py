from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import requests


def _build_chapter_text(index: int, chapter_chars: int) -> str:
    base = (
        f"第{index}章 长篇策略压测\n"
        "这是用于验证分章整理与超长章节分块策略的测试文本。"
        "剧情推进、人物弧、伏笔回收、世界规则会在段落中反复出现。\n"
    )
    seed = ("冲突升级与信息揭示。角色决策带来代价与转折。") * 50
    body = (base + seed + "\n") * 200
    return body[: max(800, chapter_chars)]


def _write_payload_files(chapters: int, chapter_chars: int, outline_chars: int) -> Dict[str, str]:
    temp_dir = Path(tempfile.gettempdir()) / f"inktrace_long_form_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    novel_path = temp_dir / "novel.txt"
    outline_path = temp_dir / "outline.txt"

    with novel_path.open("w", encoding="utf-8") as f:
        for i in range(1, chapters + 1):
            f.write(_build_chapter_text(i, chapter_chars))
            f.write("\n\n")

    outline_seed = (
        "总纲：主线围绕权力博弈与成长弧展开。"
        "请保持因果连续、伏笔可追踪、人物动机一致。"
    )
    outline_text = (outline_seed * 2000)[: max(2000, outline_chars)]
    outline_path.write_text(outline_text, encoding="utf-8")
    return {"novel_path": str(novel_path), "outline_path": str(outline_path), "temp_dir": str(temp_dir)}


def _create_novel(session: requests.Session, base_url: str, title: str) -> str:
    payload = {
        "title": title,
        "author": "strategy-bot",
        "genre": "xuanhuan",
        "target_word_count": 8000000,
        "summary": "",
        "tags": [],
    }
    resp = session.post(f"{base_url}/api/novels/", json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return str(data.get("id") or "")


def _delete_novel(session: requests.Session, base_url: str, novel_id: str) -> None:
    if not novel_id:
        return
    try:
        session.delete(f"{base_url}/api/novels/{novel_id}", timeout=20)
    except Exception:
        pass


def _run_import_and_check(
    session: requests.Session,
    base_url: str,
    novel_id: str,
    novel_path: str,
    outline_path: str,
    timeout_sec: int,
) -> Dict[str, object]:
    resp = session.post(
        f"{base_url}/api/content/import",
        json={"novel_id": novel_id, "file_path": novel_path, "outline_path": outline_path},
        timeout=timeout_sec,
    )
    resp.raise_for_status()
    payload = resp.json()

    progress_resp = session.get(f"{base_url}/api/content/organize/progress/{novel_id}", timeout=20)
    progress_resp.raise_for_status()
    progress = progress_resp.json()
    return {"import": payload, "progress": progress}


def _run_single_case(
    *,
    session: requests.Session,
    base_url: str,
    case_name: str,
    chapters: int,
    chapter_chars: int,
    outline_chars: int,
    timeout_sec: int,
    keep_data: bool,
) -> Dict[str, object]:
    payload_files = _write_payload_files(chapters, chapter_chars, outline_chars)
    novel_id = ""
    started_at = time.time()
    try:
        novel_id = _create_novel(session, base_url, f"{case_name}-{int(started_at)}")
        result = _run_import_and_check(
            session,
            base_url,
            novel_id,
            payload_files["novel_path"],
            payload_files["outline_path"],
            timeout_sec,
        )
        import_payload = result["import"]
        progress = result["progress"]
        analysis_status = str(import_payload.get("analysis_status") or "").strip()
        analysis_error = str(import_payload.get("analysis_error") or "").strip()
        strategy = str(progress.get("strategy") or "").strip()
        chunked_count = int(progress.get("chunked_chapter_count") or 0)
        elapsed_sec = int(time.time() - started_at)

        ok = True
        fail_code = 0
        fail_reason = ""
        if "上下文不足" in analysis_error or "MODEL_CONTEXT_TOO_SMALL" in analysis_error:
            ok = False
            fail_code = 2
            fail_reason = f"still hard-failed by model context: {analysis_error}"
        elif analysis_status not in {"done", "failed"}:
            ok = False
            fail_code = 3
            fail_reason = f"unexpected analysis_status={analysis_status}"
        elif strategy and strategy != "chunked_chapter_first":
            ok = False
            fail_code = 4
            fail_reason = f"unexpected strategy={strategy}"

        return {
            "ok": ok,
            "fail_code": fail_code,
            "fail_reason": fail_reason,
            "case_name": case_name,
            "analysis_status": analysis_status,
            "analysis_error": analysis_error,
            "strategy": strategy or "n/a",
            "chunked_chapter_count": chunked_count,
            "elapsed_sec": elapsed_sec,
            "import_payload": import_payload,
            "progress": progress,
            "novel_id": novel_id,
            "payload_files": payload_files,
        }
    finally:
        if not keep_data:
            _delete_novel(session, base_url, novel_id)
            try:
                Path(payload_files["novel_path"]).unlink(missing_ok=True)
                Path(payload_files["outline_path"]).unlink(missing_ok=True)
                Path(payload_files["temp_dir"]).rmdir()
            except Exception:
                pass


def _print_case_result(case_result: Dict[str, object]) -> None:
    print(f"[CASE] {case_result['case_name']}")
    print("[IMPORT]")
    print(json.dumps(case_result.get("import_payload") or {}, ensure_ascii=False, indent=2)[:2000])
    print("[PROGRESS]")
    print(json.dumps(case_result.get("progress") or {}, ensure_ascii=False, indent=2))
    if not bool(case_result.get("ok")):
        print(f"[FAIL] {case_result.get('fail_reason')}")
        return
    print(
        f"[OK] status={case_result.get('analysis_status')} strategy={case_result.get('strategy')} "
        f"chunked_chapter_count={case_result.get('chunked_chapter_count')} elapsed={case_result.get('elapsed_sec')}s"
    )


def _print_compare_report(results: List[Dict[str, object]]) -> None:
    print("[COMPARE]")
    for item in results:
        print(
            f"  - {item.get('case_name')}: "
            f"status={item.get('analysis_status')}, "
            f"strategy={item.get('strategy')}, "
            f"chunked={item.get('chunked_chapter_count')}, "
            f"elapsed={item.get('elapsed_sec')}s"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Long-form organize strategy replay (chapter-first + chunking + outline digest).")
    parser.add_argument("--base-url", default="http://127.0.0.1:9527")
    parser.add_argument("--chapters", type=int, default=120, help="Chapter count for synthetic novel")
    parser.add_argument("--chapter-chars", type=int, default=3000, help="Approx chars per chapter")
    parser.add_argument("--outline-chars", type=int, default=50000, help="Outline chars")
    parser.add_argument("--timeout-sec", type=int, default=1200, help="Import endpoint timeout")
    parser.add_argument("--keep-data", action="store_true", help="Keep generated novel and temp files for inspection")
    parser.add_argument("--compare", action="store_true", help="Run built-in 8k/32k profile comparison")
    args = parser.parse_args()
    session = requests.Session()
    base_url = args.base_url.rstrip("/")
    if not args.compare:
        result = _run_single_case(
            session=session,
            base_url=base_url,
            case_name="single",
            chapters=args.chapters,
            chapter_chars=args.chapter_chars,
            outline_chars=args.outline_chars,
            timeout_sec=args.timeout_sec,
            keep_data=args.keep_data,
        )
        _print_case_result(result)
        return int(result.get("fail_code") or 0)

    profiles = [
        {"case_name": "8k_profile", "chapters": 120, "chapter_chars": 5000, "outline_chars": 50000},
        {"case_name": "32k_profile", "chapters": 120, "chapter_chars": 2500, "outline_chars": 30000},
    ]
    results: List[Dict[str, object]] = []
    for profile in profiles:
        case_result = _run_single_case(
            session=session,
            base_url=base_url,
            case_name=str(profile["case_name"]),
            chapters=int(profile["chapters"]),
            chapter_chars=int(profile["chapter_chars"]),
            outline_chars=int(profile["outline_chars"]),
            timeout_sec=args.timeout_sec,
            keep_data=args.keep_data,
        )
        results.append(case_result)
        _print_case_result(case_result)
        if not bool(case_result.get("ok")):
            _print_compare_report(results)
            return int(case_result.get("fail_code") or 1)

    _print_compare_report(results)
    print("[OK] compare mode passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
