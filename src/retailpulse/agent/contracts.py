"""Public, closed contracts shared by CLI and future application adapters."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    field_validator,
    model_validator,
)

Identifier = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9_]{1,64}$")]
Metric = Literal["units", "revenue_proxy", "known_revenue_proxy", "price_coverage",
                 "rolling_7d", "rolling_28d", "demand_spike_flag", "data_freshness"]
Model = Literal["last_value", "rolling_mean", "seasonal_naive_7", "lightgbm_global_v1"]
Number = StrictInt | StrictFloat | None


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Period(Contract):
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start > self.end or (self.end - self.start).days > 3660:
            raise ValueError("Use an ordered date interval of at most 3661 days.")
        return self


class Filters(Contract):
    store: Identifier | None = None
    department: Identifier | None = None
    item: Identifier | None = None

    @field_validator("start_date", "end_date", mode="before", check_fields=False)
    @classmethod
    def iso_dates(cls, value):
        if value is not None and type(value) is not date and not (isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-"):
            raise ValueError("Dates must be date objects or ISO YYYY-MM-DD strings.")
        return value


class KpiRequest(Filters):
    metric: Metric
    start_date: date | None = None
    end_date: date | None = None
    granularity: Literal["total", "day", "month", "week", "store", "department"] = "total"
    comparison: Literal["previous_period"] | None = None
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 100

    @model_validator(mode="after")
    def dates(self):
        if self.metric == "data_freshness":
            if self.start_date or self.end_date or self.store or self.department or self.item or self.granularity != "total" or self.comparison:
                raise ValueError("data_freshness is a global snapshot; segment and date filters are unsupported.")
        elif not self.start_date or not self.end_date:
            raise ValueError("Both start_date and end_date are required for sales metrics.")
        else:
            Period(start=self.start_date, end=self.end_date)
        if self.comparison and self.metric != "units":
            raise ValueError("Previous-period comparison supports units only.")
        return self


class ForecastRequest(Filters):
    models: tuple[Model, ...] = ("lightgbm_global_v1",)
    split: Literal["validation", "test", "future"]
    start_date: date | None = None
    end_date: date | None = None
    horizon: Annotated[int, Field(strict=True, ge=1, le=366)] | None = None
    demand_level: Literal["zero", "low", "medium", "high"] | None = None
    segmentation: Literal["overall", "day", "store", "department", "horizon", "demand_level"] = "overall"
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 100

    @model_validator(mode="after")
    def ranges(self):
        if not 1 <= len(self.models) <= 4 or len(set(self.models)) != len(self.models):
            raise ValueError("Select one to four distinct approved models.")
        if bool(self.start_date) != bool(self.end_date):
            raise ValueError("Supply both target-date bounds or neither.")
        if self.start_date:
            Period(start=self.start_date, end=self.end_date)
        return self


class DocsRequest(Contract):
    query: Annotated[str, Field(strict=True, min_length=2, max_length=300)]
    limit: Annotated[int, Field(strict=True, ge=1, le=5)] = 3


class KpiCall(Contract):
    tool: Literal["get_kpi"]
    arguments: KpiRequest


class ForecastCall(Contract):
    tool: Literal["get_forecast"]
    arguments: ForecastRequest


class DocsCall(Contract):
    tool: Literal["search_metric_docs"]
    arguments: DocsRequest


class Plan(Contract):
    call: Annotated[KpiCall | ForecastCall | DocsCall, Field(discriminator="tool")]


class Provenance(Contract):
    source_table: str
    gold_run_id: str
    source_ingestion_ts: str
    generated_at: str
    observed_period: Period
    as_of_date: date
    data_freshness: int


class KpiPoint(Contract):
    segment: str
    value: Number
    unit: str
    period: Period
    observations: int
    missing_observations: int = 0
    previous_value: Number = None
    previous_period: Period | None = None
    change: Number = None
    change_pct: Number = None


class KpiResult(Contract):
    tool: Literal["get_kpi"] = "get_kpi"
    metric: Metric
    filters: KpiRequest
    rows: list[KpiPoint]
    provenance: Provenance
    warnings: list[str]


class ForecastPoint(Contract):
    model: Model
    split: Literal["validation", "test", "future"]
    segment: str
    period: Period
    forecast_origin_start: date
    forecast_origin_end: date
    observations: int
    predicted_units: Number
    actual_units: Number
    WMAPE: Number
    MAE: Number
    RMSE: Number
    wmape_zero_denominator: bool


class ForecastResult(Contract):
    tool: Literal["get_forecast"] = "get_forecast"
    metric: Literal["forecast"] = "forecast"
    filters: ForecastRequest
    rows: list[ForecastPoint]
    provenance: Provenance
    warnings: list[str]
    units: dict[str, str] = {"predicted_units": "units", "actual_units": "units", "WMAPE": "ratio", "MAE": "units", "RMSE": "units"}


class Excerpt(Contract):
    source_document: str
    section: str
    start_line: int
    end_line: int
    excerpt: str
    metric: str | None


class DocsResult(Contract):
    tool: Literal["search_metric_docs"] = "search_metric_docs"
    metric: str | None
    excerpts: list[Excerpt]
    warnings: list[str]


class Answer(Contract):
    request_id: str
    status: Literal["answered", "clarification", "refused", "unavailable", "error"]
    answer: str
    provider: str
    tool: Literal["get_kpi", "get_forecast", "search_metric_docs"] | None = None
    result: KpiResult | ForecastResult | DocsResult | None = None
    error_category: str | None = None
    grounding_validated: bool = False


class Trace(Contract):
    request_id: str
    time: datetime
    intent_category: str
    tool: str | None
    validated_filters: dict
    duration_ms: float
    source: str | None
    gold_run_id: str | None
    outcome: str
    error_category: str | None
    grounding_validated: bool
    provider: str
