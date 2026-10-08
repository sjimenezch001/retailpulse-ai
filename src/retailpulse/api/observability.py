"""Closed operational events: no questions, headers, URLs, parameters or exceptions."""

import hashlib
import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
Event = Literal[
    "startup", "shutdown", "api_request", "query", "readiness", "assistant", "provider"
]
LOGGER = logging.getLogger("retailpulse.events")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False
STATUSES = {
    "ok",
    "ready",
    "degraded",
    "unavailable",
    "error",
    "answered",
    "refused",
    "clarification",
    "succeeded",
    "failed",
    "not_requested",
    "not_attempted",
}
OPERATIONS = {"health", "ready", "summary", "forecast", "ask", "unknown"}
CATEGORIES = {
    "invalid_host",
    "invalid_origin",
    "query_size",
    "content_type",
    "payload_size",
    "content_length",
    "body_timeout",
    "unexpected_body",
    "invalid_request",
    "duplicate_filter",
    "query_timeout",
    "resource_limit",
    "missing_gold",
    "gold_contract",
    "mode_mismatch",
    "source_changed",
    "busy",
    "http_error",
    "internal_error",
    "model_unavailable",
    "trace_unavailable",
    "invalid_arguments",
    "no_matching_data",
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Never render getMessage(), exc_info or arbitrary third-party log fields.
        event = getattr(record, "rp_event", {"event": "unstructured_log_suppressed"})
        return json.dumps(event, separators=(",", ":"), allow_nan=False)


def configure() -> None:
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        LOGGER.addHandler(handler)


def valid_id(value: str | None) -> str | None:
    try:
        return str(UUID(value)) if value else None
    except ValueError:
        return None


def emit(
    event: Event,
    mode: str,
    *,
    component: Literal["api", "launcher"] = "api",
    status: str = "ok",
    operation: str | None = None,
    duration_ms: float | None = None,
    source_version: str | None = None,
    error_category: str | None = None,
    http_status: int | None = None,
    tool: str | None = None,
    grounded: bool | None = None,
    provider_available: bool | None = None,
    run_id: str | None = None,
) -> None:
    payload: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": valid_id(request_id.get()),
        "component": component,
        "event": event,
        "level": "ERROR" if status == "error" else "INFO",
        "mode": mode if mode in {"real", "synthetic"} else "unknown",
        "status": status if status in STATUSES else "unknown",
    }
    if operation is not None:
        payload["operation"] = operation if operation in OPERATIONS else "unknown"
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 3)
    if source_version is not None:
        payload["source_version"] = hashlib.sha256(source_version.encode()).hexdigest()
    if error_category is not None:
        payload["error_category"] = (
            error_category if error_category in CATEGORIES else "other"
        )
    if http_status is not None:
        payload["http_status"] = http_status
    if tool is not None:
        payload["tool"] = (
            tool
            if tool in {"get_kpi", "get_forecast", "search_metric_docs"}
            else "unknown"
        )
    if grounded is not None:
        payload["grounding_validated"] = grounded
    if provider_available is not None:
        payload["provider_available"] = provider_available
    if run_id is not None:
        payload["run_id"] = valid_id(run_id)
    LOGGER.info("", extra={"rp_event": payload})
