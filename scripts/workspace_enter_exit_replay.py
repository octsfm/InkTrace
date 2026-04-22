from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def timed_get(session: requests.Session, url: str, timeout: float = 8.0) -> tuple[int, int]:
    started = time.perf_counter()
    resp = session.get(url, timeout=timeout)
    duration_ms = int((time.perf_counter() - started) * 1000)
    return resp.status_code, duration_ms


def run_once(base_url: str) -> dict:
    session = requests.Session()
    latencies = {}
    novels_url = f"{base_url}/api/novels/"
    status, ms = timed_get(session, novels_url)
    latencies["novels"] = ms
    if status != 200:
        return {"ok": False, "latencies": latencies, "reason": f"novels status={status}"}

    novels = session.get(novels_url, timeout=8).json() or []
    if not novels:
        return {"ok": True, "latencies": latencies, "reason": "no_novels"}
    novel_id = str(novels[0].get("id") or "").strip()
    if not novel_id:
        return {"ok": False, "latencies": latencies, "reason": "missing novel id"}

    endpoints = [
        ("novel_detail", f"{base_url}/api/novels/{novel_id}"),
        ("novel_chapters", f"{base_url}/api/novels/{novel_id}/chapters"),
        ("project_by_novel", f"{base_url}/api/v2/projects/by-novel/{novel_id}"),
        ("organize_progress", f"{base_url}/api/content/organize/progress/{novel_id}"),
    ]
    with ThreadPoolExecutor(max_workers=len(endpoints)) as executor:
        future_map = {
            executor.submit(timed_get, session, url): name
            for name, url in endpoints
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                status_code, duration_ms = future.result()
                latencies[name] = duration_ms
                if status_code >= 500:
                    return {"ok": False, "latencies": latencies, "reason": f"{name} status={status_code}"}
            except Exception as exc:
                return {"ok": False, "latencies": latencies, "reason": f"{name} error={exc}"}

    return {"ok": True, "latencies": latencies, "reason": ""}


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay workspace enter/exit flow for regression verification.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9527", help="Backend base URL")
    parser.add_argument("--loops", type=int, default=10, help="Loop count")
    parser.add_argument("--max-p95-ms", type=int, default=800, help="Fail if p95 of detail requests exceeds this")
    args = parser.parse_args()

    detail_samples = []
    for i in range(args.loops):
        result = run_once(args.base_url.rstrip("/"))
        if not result["ok"]:
            print(f"[FAIL] loop={i + 1} reason={result['reason']} latencies={result['latencies']}")
            return 1
        samples = [v for k, v in result["latencies"].items() if k != "novels"]
        detail_samples.extend(samples)
        print(f"[OK] loop={i + 1} latencies={result['latencies']}")

    if not detail_samples:
        print("[OK] no detail samples (novel list empty)")
        return 0

    sorted_samples = sorted(detail_samples)
    p95_index = int((len(sorted_samples) - 1) * 0.95)
    p95 = sorted_samples[p95_index]
    avg = int(statistics.mean(sorted_samples))
    print(f"[SUMMARY] samples={len(sorted_samples)} avg={avg}ms p95={p95}ms max={sorted_samples[-1]}ms")
    if p95 > args.max_p95_ms:
        print(f"[FAIL] p95 {p95}ms exceeds threshold {args.max_p95_ms}ms")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
