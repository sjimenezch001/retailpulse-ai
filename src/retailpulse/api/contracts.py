"""Closed HTTP contracts around the existing agent contracts."""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from retailpulse.agent.contracts import (
    Answer,
    Contract,
    Filters,
    ForecastRequest,
    ForecastResult,
    KpiResult,
    Model,
    Period,
    Provenance,
)

Mode = Literal["real", "synthetic"]
ProviderMode = Literal["ollama", "deterministic", "auto"]


class ForecastWindow(Contract):
    model: str
    split: str
    start: date
    end: date
    max_horizon: int


class Dataset(Contract):
    mode: Mode
    label: str
    dataset_version: str
    generation_timestamp: str
    lineage: Provenance
    stores: list[str]
    departments: list[str]
    forecast_windows: list[ForecastWindow]


class ProviderState(Contract):
    available: bool
    model: str
    default_mode: ProviderMode


class Health(Contract):
    status: Literal["ok", "degraded"]
    api_version: str = "rp10-v1"
    project_version: str = "0.1.0"
    mode: Mode
    dataset_available: bool
    dataset: Dataset | None
    provider: ProviderState
    message: str


class SummaryQuery(Filters):
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def dates(self):
        if bool(self.start_date) != bool(self.end_date):
            raise ValueError("Supply both date bounds or neither.")
        if self.start_date:
            Period(start=self.start_date, end=self.end_date)
        return self


class ForecastQuery(ForecastRequest):
    """HTTP query strings are decoded, then revalidated by ForecastRequest."""

    split: Literal["validation", "test", "future"] = "test"
    models: tuple[Model, ...] = ("lightgbm_global_v1", "rolling_mean")
    horizon: Annotated[int, Field(ge=1, le=366)] | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 100

    @model_validator(mode="after")
    def approved(self):
        ForecastRequest.model_validate(self.model_dump())
        return self


class Summary(Contract):
    dataset: Dataset
    filters: SummaryQuery
    metrics: dict[str, KpiResult]
    daily_trend: KpiResult
    stores: KpiResult
    departments: KpiResult
    cached: bool = False


class ForecastResponse(Contract):
    dataset: Dataset
    result: ForecastResult
    cached: bool = False


class AssistantQuery(Contract):
    question: Annotated[str, Field(strict=True, min_length=2, max_length=1000)]
    provider: ProviderMode = "ollama"


class AssistantResponse(Contract):
    dataset: Dataset
    result: Answer
    latency_ms: float
    live_provider_succeeded: bool


class ErrorDetail(Contract):
    code: str
    message: str
    request_id: str


class ErrorResponse(Contract):
    error: ErrorDetail
