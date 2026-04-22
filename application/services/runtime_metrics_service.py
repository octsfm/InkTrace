from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict, List


_lock = threading.Lock()
_started_at = time.time()
_slow_request_threshold_ms = 800
_max_samples = 400

_request_metrics = {
    "requests_total": 0,
    "requests_failed_total": 0,
    "slow_requests_total": 0,
    "inflight_requests": 0,
}
_duration_samples: Deque[int] = deque(maxlen=_max_samples)
_path_samples: Dict[str, Deque[int]] = {}
_alerts: Deque[dict] = deque(maxlen=40)
_organize_metrics = {
    "token_limit_errors": 0,
    "budget_blocks": 0,
    "batch_resume_total": 0,
    "batch_resume_success": 0,
    "global_analysis_total": 0,
}
_global_analysis_duration_samples: Deque[int] = deque(maxlen=240)
_consecutive_budget_blocks = 0


def mark_request_start() -> None:
    with _lock:
        _request_metrics["inflight_requests"] += 1


def mark_request_finish(path: str, status_code: int, duration_ms: int) -> None:
    path_key = str(path or "")
    duration_ms = int(max(0, duration_ms))
    with _lock:
        _request_metrics["requests_total"] += 1
        _request_metrics["inflight_requests"] = max(0, int(_request_metrics["inflight_requests"]) - 1)
        if int(status_code) >= 400:
            _request_metrics["requests_failed_total"] += 1
        if duration_ms >= _slow_request_threshold_ms:
            _request_metrics["slow_requests_total"] += 1
        _duration_samples.append(duration_ms)
        if path_key not in _path_samples:
            _path_samples[path_key] = deque(maxlen=80)
        _path_samples[path_key].append(duration_ms)


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    idx = int((len(values) - 1) * p)
    idx = max(0, min(idx, len(values) - 1))
    return int(values[idx])


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 4)


def _push_alert(code: str, message: str, severity: str = "high") -> None:
    _alerts.append(
        {
            "ts": int(time.time()),
            "code": str(code or ""),
            "severity": str(severity or "high"),
            "message": str(message or ""),
        }
    )


def record_budget_block() -> List[dict]:
    global _consecutive_budget_blocks
    alerts: List[dict] = []
    with _lock:
        _organize_metrics["budget_blocks"] += 1
        _consecutive_budget_blocks += 1
        if _consecutive_budget_blocks >= 3:
            _push_alert(
                "BUDGET_BLOCK_CONSECUTIVE",
                "连续 3 次 budget_block，请检查模型配置与容量规划。",
                severity="high",
            )
        alerts = list(_alerts)
    return alerts


def reset_budget_block_streak() -> None:
    global _consecutive_budget_blocks
    with _lock:
        _consecutive_budget_blocks = 0


def record_token_limit_error() -> List[dict]:
    alerts: List[dict] = []
    with _lock:
        _organize_metrics["token_limit_errors"] += 1
        token_rate = _rate(
            int(_organize_metrics["token_limit_errors"]),
            int(_organize_metrics["global_analysis_total"]) + int(_organize_metrics["token_limit_errors"]),
        )
        if token_rate > 2.0:
            _push_alert(
                "TOKEN_LIMIT_ERROR_RATE_HIGH",
                f"token_limit_error_rate={token_rate}% 超过 2%，请提升容量或调整降载策略。",
                severity="critical",
            )
        alerts = list(_alerts)
    return alerts


def record_batch_resume(success: bool) -> None:
    with _lock:
        _organize_metrics["batch_resume_total"] += 1
        if bool(success):
            _organize_metrics["batch_resume_success"] += 1


def record_global_analysis_duration(duration_ms: int) -> None:
    value = int(max(0, duration_ms))
    with _lock:
        _organize_metrics["global_analysis_total"] += 1
        _global_analysis_duration_samples.append(value)


def get_runtime_metrics_snapshot() -> dict:
    with _lock:
        durations = sorted(_duration_samples)
        global_samples = sorted(_global_analysis_duration_samples)
        path_stats = {}
        for path, samples in _path_samples.items():
            sorted_samples = sorted(samples)
            path_stats[path] = {
                "count": len(sorted_samples),
                "p95_ms": _percentile(sorted_samples, 0.95),
                "max_ms": int(sorted_samples[-1]) if sorted_samples else 0,
            }
        return {
            "uptime_sec": int(time.time() - _started_at),
            "requests": dict(_request_metrics),
            "latency_ms": {
                "p50": _percentile(durations, 0.50),
                "p95": _percentile(durations, 0.95),
                "p99": _percentile(durations, 0.99),
                "max": int(durations[-1]) if durations else 0,
            },
            "paths": path_stats,
            "slow_threshold_ms": _slow_request_threshold_ms,
            "organize": {
                "token_limit_error_rate": _rate(
                    int(_organize_metrics["token_limit_errors"]),
                    int(_organize_metrics["global_analysis_total"]) + int(_organize_metrics["token_limit_errors"]),
                ),
                "budget_block_rate": _rate(
                    int(_organize_metrics["budget_blocks"]),
                    max(1, int(_request_metrics["requests_total"])),
                ),
                "batch_resume_success_rate": _rate(
                    int(_organize_metrics["batch_resume_success"]),
                    int(_organize_metrics["batch_resume_total"]),
                ),
                "global_analysis_p95_ms": _percentile(global_samples, 0.95),
                "alerts": list(_alerts),
            },
        }
