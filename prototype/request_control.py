"""Sequential, per-process pacing. Never log provider bodies or credentials."""
import math
import random
import time
from email.utils import parsedate_to_datetime


TEMPORARY = {"rate_limit_exceeded", "slow_down", "requests", "tokens"}
BILLING = {"insufficient_quota", "billing_hard_limit_reached", "billing_not_active",
           "organization_usage_limit_exceeded", "usage_limit_reached",
           "credits_exhausted", "spend_limit_exceeded"}


def error_details(exc):
    body = getattr(exc, "body", None)
    body = body if isinstance(body, dict) else {}
    body = body.get("error", body)
    body = body if isinstance(body, dict) else {}
    code = getattr(exc, "code", None) or body.get("code")
    kind = body.get("type") or getattr(exc, "type", None)
    code = code if isinstance(code, str) else None
    kind = kind if isinstance(kind, str) else None
    status = getattr(exc, "status_code", None)
    # Only known codes are exposed; arbitrary provider text may contain secrets.
    billing = code in BILLING or kind in BILLING
    transient = status == 429 and not billing and code in TEMPORARY
    return {"error_type": type(exc).__name__, "http_status": status if isinstance(status, int) else None,
            "error_code": code if code in TEMPORARY | BILLING else (kind if kind in BILLING else "unclassified"),
            "category": "quota_or_billing" if billing else ("temporary_rate_limit" if transient else "non_retryable")}


def retry_after(exc, wall_clock):
    headers = getattr(getattr(exc, "response", None), "headers", {})
    values = []
    for key, scale in (("retry-after-ms", 0.001), ("retry-after", 1)):
        raw = headers.get(key)
        if raw is None:
            continue
        try:
            value = float(raw) * scale
        except (ValueError, TypeError):
            try:
                value = parsedate_to_datetime(raw).timestamp() - wall_clock()
            except (ValueError, TypeError, OverflowError):
                continue
        if math.isfinite(value):
            values.append(max(0, value))
    return max(values, default=0)


class RequestController:
    def __init__(self, interval=2.0, retries=2, max_wait=30.0, *, clock=time.monotonic,
                 sleep=time.sleep, wall_clock=time.time, jitter=random.random):
        if not math.isfinite(interval) or not 0 <= interval <= 60:
            raise ValueError("interval must be between 0 and 60 seconds")
        if not isinstance(retries, int) or not 0 <= retries <= 5:
            raise ValueError("retries must be between 0 and 5")
        if not math.isfinite(max_wait) or not 0 <= max_wait <= 60:
            raise ValueError("max_wait must be between 0 and 60 seconds")
        self.interval, self.retries, self.max_wait = interval, retries, max_wait
        self.clock, self.sleep, self.wall_clock, self.jitter = clock, sleep, wall_clock, jitter
        self.next_start = 0
        self.stop_reason = None

    def call(self, operation):
        attempts = []
        if self.stop_reason:
            return None, {"attempts": attempts, "skipped": True, "stop_reason": self.stop_reason}
        for index in range(self.retries + 1):
            delay = max(0, self.next_start - self.clock())
            if delay:
                self.sleep(delay)
            started = self.clock()
            self.next_start = started + self.interval
            row = {"attempt": index + 1, "delay_seconds": delay}
            attempts.append(row)
            try:
                answer = operation(index + 1)
                row["status"] = "received"
                return answer, {"attempts": attempts}
            except Exception as exc:
                details = error_details(exc)
                row.update(status="error", **details)
                if details["category"] == "quota_or_billing":
                    self.stop_reason = "quota_or_billing"
                if details["category"] != "temporary_rate_limit":
                    return None, {"attempts": attempts, **details}
                wait = max(retry_after(exc, self.wall_clock), min(2 ** index, 16) + self.jitter())
                self.next_start = max(self.next_start, self.clock() + wait)
                if wait > self.max_wait:
                    self.stop_reason = "retry_delay_exceeds_budget"
                elif index == self.retries:
                    self.stop_reason = "retry_budget_exhausted"
                if self.stop_reason:
                    return None, {"attempts": attempts, **details, "stop_reason": self.stop_reason}
