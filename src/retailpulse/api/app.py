"""Local-only FastAPI surface with closed requests and sanitized JSON errors."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from retailpulse.agent.errors import AgentError
from retailpulse.api import observability
from retailpulse.api.contracts import (
    AssistantQuery,
    AssistantResponse,
    ErrorResponse,
    ForecastQuery,
    ForecastResponse,
    Health,
    Readiness,
    Summary,
    SummaryQuery,
)
from retailpulse.api.service import Service
from retailpulse.api.source import ApiSettings, portable_database


def error(status, code, message, request_id):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


class RequestLog:
    """Own correlation IDs; suppress raw request details and exception tracebacks."""

    def __init__(self, app, mode):
        self.app, self.mode = app, mode

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        identifier = str(uuid4())
        scope.setdefault("state", {})["request_id"] = identifier
        token = observability.request_id.set(identifier)
        started, status, responded = perf_counter(), 500, False

        async def safe_send(message):
            nonlocal status, responded
            if message["type"] == "http.response.start":
                status, responded = message["status"], True
                message["headers"] = [*message.get("headers", []),
                    (b"x-request-id", identifier.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store")]
            await send(message)

        try:
            await self.app(scope, receive, safe_send)
        except Exception:
            scope["state"]["error_category"] = "internal_error"
            if not responded:
                await error(500, "internal_error", "The request could not be completed safely.", identifier)(scope, receive, safe_send)
        finally:
            operation = {"/health": "health", "/ready": "ready", "/metrics/summary": "summary", "/forecast": "forecast", "/assistant/query": "ask"}.get(scope.get("path"), "unknown")
            observability.emit("api_request", self.mode,
                status="error" if status >= 500 else "refused" if status >= 400 else "ok",
                operation=operation, http_status=status,
                duration_ms=(perf_counter() - started) * 1000,
                error_category=scope["state"].get("error_category"))
            observability.request_id.reset(token)


class RequestBounds:
    """Bound streamed bodies too; Content-Length alone is not trusted."""

    def __init__(self, app, ui_port):
        self.app, self.ui_port = app, ui_port

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = scope.setdefault("state", {}).setdefault("request_id", str(uuid4()))
        headers = dict(scope["headers"])

        async def reject(status, code, message):
            scope["state"]["error_category"] = code
            await error(status, code, message, request_id)(scope, receive, send)

        host = headers.get(b"host", b"").decode("latin1").split(":")[0]
        if host not in {"127.0.0.1", "localhost"}:
            return await reject(
                400, "invalid_host", "Only loopback hosts are supported."
            )
        origin = headers.get(b"origin")
        if origin:
            try:
                url = urlsplit(origin.decode("latin1"))
                allowed = (
                    url.scheme == "http"
                    and url.hostname in {"127.0.0.1", "localhost"}
                    and url.port == self.ui_port
                    and not url.username
                    and not url.password
                )
            except ValueError:
                allowed = False
            if not allowed:
                return await reject(
                    403,
                    "invalid_origin",
                    "Cross-origin browser requests are not supported.",
                )
        if len(scope.get("query_string", b"")) > 2048:
            return await reject(
                414, "query_size", "The query string exceeds the supported limit."
            )
        if (
            scope["method"] == "POST"
            and headers.get(b"content-type", b"").split(b";")[0] != b"application/json"
        ):
            return await reject(415, "content_type", "Use application/json.")
        try:
            length = int(headers.get(b"content-length", b"0"))
            if not 0 <= length <= 4096:
                return await reject(
                    413, "payload_size", "The payload exceeds 4096 bytes."
                )
        except ValueError:
            return await reject(400, "content_length", "Invalid content length.")
        body = bytearray()
        deadline = asyncio.get_running_loop().time() + 5
        while True:
            try:
                message = await asyncio.wait_for(
                    receive(),
                    timeout=max(0, deadline - asyncio.get_running_loop().time()),
                )
            except TimeoutError:
                return await reject(
                    408, "body_timeout", "The request body was not received in time."
                )
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 4096:
                return await reject(
                    413, "payload_size", "The payload exceeds 4096 bytes."
                )
            if not message.get("more_body", False):
                break
        if scope["method"] == "GET" and body:
            return await reject(
                400, "unexpected_body", "GET requests do not accept a body."
            )
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings: ApiSettings) -> FastAPI:
    service = Service(settings)
    observability.configure()

    @asynccontextmanager
    async def lifespan(app):
        observability.emit("startup", settings.mode)
        yield
        observability.emit("shutdown", settings.mode)

    app = FastAPI(
        title="RetailPulse AI",
        version="rp10-v1",
        description="Local historical retail analytics. No unrestricted SQL or current inventory claims.",
        lifespan=lifespan,
        responses={
            code: {"model": ErrorResponse}
            for code in (400, 403, 408, 413, 414, 415, 422, 500, 503, 504)
        },
    )
    app.state.service = service
    app.add_middleware(RequestBounds, ui_port=settings.ui_port)
    app.add_middleware(RequestLog, mode=settings.mode)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid(request, exc):
        request.state.error_category = "invalid_request"
        return error(
            422,
            "invalid_request",
            "Use only approved fields, identifiers, providers and ordered date bounds.",
            request.state.request_id,
        )

    @app.exception_handler(AgentError)
    async def failed(request, exc):
        request.state.error_category = exc.category
        code = (
            504
            if exc.category == "query_timeout"
            else 503
            if exc.status == "unavailable"
            else 403
            if exc.status == "refused"
            else 422
        )
        return error(code, exc.category, str(exc), request.state.request_id)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        request.state.error_category = "http_error"
        return error(
            exc.status_code,
            "http_error",
            "The requested route or method is unavailable.",
            request.state.request_id,
        )

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return error(
            500,
            "internal_error",
            "The request could not be completed safely.",
            getattr(request.state, "request_id", str(uuid4())),
        )

    def run(request: Request, function, *args):
        keys = [k for k, _ in request.query_params.multi_items()]
        # Repeated model values are intentionally supported by the forecast contract.
        if any(keys.count(k) > 1 for k in keys if k != "models"):
            raise AgentError("duplicate_filter", "Supply one value for each filter.")
        if not service.slots.acquire(blocking=False):
            raise AgentError(
                "busy", "The local demo is busy. Retry shortly.", "unavailable"
            )
        try:
            started = perf_counter()
            succeeded = False
            result = function(*args)
            succeeded = True
            return result
        finally:
            service.slots.release()
            observability.emit("query", settings.mode, status="ok" if succeeded else "error",
                operation="ready" if function.__name__ == "readiness" else function.__name__,
                duration_ms=(perf_counter() - started) * 1000)

    @app.get("/health", response_model=Health)
    def health(request: Request):
        if request.query_params:
            raise AgentError("invalid_request", "Health does not accept filters.")
        return run(request, service.health)

    @app.get("/metrics/summary", response_model=Summary)
    def summary(request: Request, filters: Annotated[SummaryQuery, Query()]):
        return run(request, service.summary, filters)

    @app.get("/ready", response_model=Readiness, responses={503: {"model": Readiness | ErrorResponse}})
    def ready(request: Request):
        if request.query_params:
            raise AgentError("invalid_request", "Readiness does not accept filters.")
        result = run(request, service.readiness)
        return JSONResponse(status_code=200 if result.dataset_available else 503,
                            content=result.model_dump(mode="json"))

    @app.get("/forecast", response_model=ForecastResponse)
    def forecast(request: Request, filters: Annotated[ForecastQuery, Query()]):
        return run(request, service.forecast, filters)

    @app.post("/assistant/query", response_model=AssistantResponse)
    def ask(request: Request, question: AssistantQuery):
        if request.query_params:
            raise AgentError(
                "invalid_request", "Assistant arguments belong in the JSON body."
            )
        return run(request, service.ask, question)

    return app


def from_environment():
    root = Path(os.environ.get("RETAILPULSE_ROOT", Path.cwd())).resolve()
    mode = os.environ.get("RETAILPULSE_DEMO_MODE", "real")
    if mode not in {"real", "synthetic"}:
        raise ValueError("Invalid demonstration mode")
    database = (
        portable_database(root / "artifacts/web_demo/synthetic")
        if mode == "synthetic"
        else Path(
            os.environ.get(
                "RETAILPULSE_DATABASE", root / "data/processed/gold/retailpulse.duckdb"
            )
        )
    )
    return create_app(
        ApiSettings(
            root,
            database,
            mode=mode,
            provider=os.environ.get("RETAILPULSE_PROVIDER", "ollama"),
            ui_port=int(os.environ.get("RETAILPULSE_UI_PORT", "8501")),
        )
    )
