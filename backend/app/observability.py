from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()

_total_requests = 0
_total_errors = 0
_auth_failures = 0
_rate_limits = 0
_lockouts = 0
_endpoint_status_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))


def _status_family(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "2xx"
    if 300 <= status_code < 400:
        return "3xx"
    if 400 <= status_code < 500:
        return "4xx"
    if 500 <= status_code < 600:
        return "5xx"
    return "other"


def record_response(path: str, status_code: int) -> None:
    global _total_requests, _total_errors

    with _lock:
        _total_requests += 1
        if status_code >= 500:
            _total_errors += 1
        _endpoint_status_counts[path][_status_family(status_code)] += 1


def record_auth_failure() -> None:
    global _auth_failures
    with _lock:
        _auth_failures += 1


def record_rate_limit() -> None:
    global _rate_limits
    with _lock:
        _rate_limits += 1


def record_lockout() -> None:
    global _lockouts
    with _lock:
        _lockouts += 1


def get_metrics_snapshot() -> dict[str, object]:
    with _lock:
        endpoint_copy = {
            path: dict(counts) for path, counts in _endpoint_status_counts.items()
        }
        return {
            "total_requests": _total_requests,
            "total_errors": _total_errors,
            "auth_failures": _auth_failures,
            "rate_limits": _rate_limits,
            "lockouts": _lockouts,
            "endpoint_status_counts": endpoint_copy,
        }


def reset_metrics() -> None:
    global _total_requests, _total_errors, _auth_failures, _rate_limits, _lockouts

    with _lock:
        _total_requests = 0
        _total_errors = 0
        _auth_failures = 0
        _rate_limits = 0
        _lockouts = 0
        _endpoint_status_counts.clear()
