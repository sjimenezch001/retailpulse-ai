"""Only approved aggregates leave Gold; all variable values are SQL parameters."""
from datetime import timedelta
from pathlib import Path

from retailpulse.agent.contracts import (
    ForecastPoint,
    ForecastRequest,
    ForecastResult,
    KpiPoint,
    KpiRequest,
    KpiResult,
    Period,
    Provenance,
)
from retailpulse.agent.database import gold_session
from retailpulse.agent.errors import AgentError

# SQL fragments are developer-owned constants selected only by validated enums.
KPI_EXPRESSIONS = {
    "units": ("sum(units)::BIGINT", "units", "0"),
    "revenue_proxy": ("CASE WHEN count(sell_price)=count(*) THEN sum(revenue_proxy) END", "proxy currency units", "count(*)-count(sell_price)"),
    "known_revenue_proxy": ("sum(revenue_proxy)", "proxy currency units (known-price subset)", "count(*)-count(sell_price)"),
    "price_coverage": ("count(sell_price)::DOUBLE/nullif(count(*),0)", "ratio", "count(*)-count(sell_price)"),
    "rolling_7d": ("sum(rolling_7d)", "units/day (mean daily rolling demand)", "count(*)-count(rolling_7d)"),
    "rolling_28d": ("sum(rolling_28d)", "units/day (mean daily rolling demand)", "count(*)-count(rolling_28d)"),
    "demand_spike_flag": ("count(*) FILTER(WHERE demand_spike_flag)", "item/store/day flags", "0"),
}
KPI_GROUPS = {"total": "'all'", "day": "CAST(date AS VARCHAR)", "month": "strftime(date,'%Y-%m')",
              "week": "CAST(wm_yr_wk AS VARCHAR)", "store": "store_id", "department": "dept_id"}
FORECAST_GROUPS = {"overall": "'all'", "day": "CAST(target_date AS VARCHAR)", "store": "store_id",
                   "department": "dept_id", "horizon": "CAST(horizon AS VARCHAR)", "demand_level": "demand_level"}
FILTER_SQL = "(? IS NULL OR store_id=?) AND (? IS NULL OR dept_id=?) AND (? IS NULL OR item_id=?)"
HISTORICAL = "Historical M5 snapshot; these observations do not describe current sales or inventory."


def metadata(db, source):
    records = db.execute("SELECT gold_run_id,source_ingestion_ts,generated_at,first_sales_date,last_sales_date,as_of_date FROM pipeline_metadata").fetchall()
    if len(records) != 1 or any(value is None or value == "" for value in records[0]):
        raise AgentError("missing_provenance", "Gold requires one complete source lineage record.", "unavailable")
    run, ingestion, generated, start, end, as_of = records[0]
    if as_of < end:
        raise AgentError("invalid_freshness", "The Gold freshness date is invalid.", "unavailable")
    return Provenance(source_table=source, gold_run_id=run, source_ingestion_ts=ingestion,
                      generated_at=generated, observed_period=Period(start=start, end=end),
                      as_of_date=as_of, data_freshness=(as_of-end).days)


def validate_filters(db, request):
    for value, statement, label in (
        (request.store, "SELECT count(*) FROM dim_store WHERE store_id=?", "store"),
        (request.department, "SELECT count(*) FROM dim_product WHERE dept_id=?", "department"),
        (request.item, "SELECT count(*) FROM dim_product WHERE item_id=?", "item"),
    ):
        if value and not db.execute(statement, [value]).fetchone()[0]:
            raise AgentError("invalid_filter", f"The requested {label} is not in the Gold pilot.")
    if request.item and request.department and not db.execute("SELECT count(*) FROM dim_product WHERE item_id=? AND dept_id=?", [request.item, request.department]).fetchone()[0]:
        raise AgentError("incompatible_filters", "That item does not belong to the selected department.")


def filter_values(request):
    return [v for v in (request.store, request.department, request.item) for _ in range(2)]


def bounded_rows(cursor, limit):
    records = cursor.fetchmany(limit + 1)
    if len(records) > limit:
        raise AgentError("row_limit", "The result exceeds the response row limit. Use a coarser grain or narrower period.")
    return records


class GoldTools:
    """The configured database path is application-owned, never supplied by a tool call."""
    def __init__(self, database: Path, *, timeout_seconds=5.0):
        self.database = Path(database)
        self.timeout_seconds = timeout_seconds

    def observed_period(self):
        with gold_session(self.database, self.timeout_seconds) as db:
            return metadata(db, "pipeline_metadata").observed_period

    def get_kpi(self, request: KpiRequest) -> KpiResult:
        request = KpiRequest.model_validate(request.model_dump() if isinstance(request, KpiRequest) else request)
        with gold_session(self.database, self.timeout_seconds) as db:
            source = metadata(db, "pipeline_metadata" if request.metric == "data_freshness" else "mart_sales_daily")
            warnings = [HISTORICAL]
            if request.metric == "data_freshness":
                rows = [KpiPoint(segment="all", value=source.data_freshness, unit="days", period=source.observed_period, observations=1)]
            else:
                validate_filters(db, request)
                if request.start_date < source.observed_period.start or request.end_date > source.observed_period.end:
                    raise AgentError("unobserved_period", f"Sales are observed only from {source.observed_period.start} to {source.observed_period.end}; choose an interval inside that historical range.")
                catalog_metric = "revenue_proxy" if request.metric in ("known_revenue_proxy", "price_coverage") else request.metric
                if not db.execute("SELECT count(*) FROM metric_definitions WHERE metric=?", [catalog_metric]).fetchone()[0]:
                    raise AgentError("unapproved_metric", "The requested metric lacks its canonical Gold definition.", "unavailable")
                rows = self._kpi_rows(db, request)
                if request.comparison:
                    days = (request.end_date-request.start_date).days + 1
                    previous = request.model_copy(update={"start_date": request.start_date-timedelta(days=days), "end_date": request.start_date-timedelta(days=1), "comparison": None})
                    if previous.start_date < source.observed_period.start or request.granularity not in ("total", "store", "department"):
                        raise AgentError("comparison_period", "Previous-period comparison needs a complete preceding interval and total/store/department granularity.")
                    prior = {row.segment: row for row in self._kpi_rows(db, previous)}
                    rows = [row.model_copy(update={"previous_value": prior[row.segment].value,
                            "previous_period": prior[row.segment].period,
                            "change": row.value-prior[row.segment].value,
                            "change_pct": (row.value-prior[row.segment].value)/prior[row.segment].value if prior[row.segment].value else None}) if row.segment in prior else row for row in rows]
                if request.metric in ("revenue_proxy", "known_revenue_proxy"):
                    warnings.append("revenue_proxy is units times sell_price, not audited revenue. Known revenue includes only observations with known prices.")
                if any(row.missing_observations for row in rows):
                    warnings.append("Some observations lack prices or sufficient rolling history; missing values remain explicit and are not zero-filled.")
                if request.metric.startswith("rolling_"):
                    warnings.append("Rolling demand sums series within each day, then averages valid daily sums over the selected period; it is not additive across dates.")
                if request.metric == "demand_spike_flag":
                    warnings.append("Spike flags are heuristic review signals, not confirmed causes or stockouts.")
            if not rows:
                warnings.append("No matching observations; no numerical value is available.")
            return KpiResult(metric=request.metric, filters=request, rows=rows, provenance=source, warnings=warnings)

    @staticmethod
    def _kpi_rows(db, request):
        expression, unit, missing = KPI_EXPRESSIONS[request.metric]
        group = KPI_GROUPS[request.granularity]
        if request.metric.startswith("rolling_"):
            statement = f"""WITH daily AS (SELECT {group} segment,date,{expression} AS metric_value,
                count(*) observations,{missing} missing FROM mart_sales_daily
                WHERE date BETWEEN ? AND ? AND {FILTER_SQL} GROUP BY segment,date)
                SELECT segment,avg(metric_value),min(date),max(date),sum(observations),sum(missing)
                FROM daily GROUP BY segment ORDER BY segment LIMIT ?"""
        else:
            statement = f"""SELECT {group} segment,{expression},min(date),max(date),count(*),{missing}
                FROM mart_sales_daily WHERE date BETWEEN ? AND ? AND {FILTER_SQL}
                GROUP BY segment ORDER BY segment LIMIT ?"""
        records = bounded_rows(db.execute(statement, [request.start_date, request.end_date, *filter_values(request), request.limit+1]), request.limit)
        return [KpiPoint(segment=str(segment), value=value, unit=unit, period=Period(start=start, end=end), observations=n, missing_observations=missing_n)
                for segment, value, start, end, n, missing_n in records]

    def get_forecast(self, request: ForecastRequest) -> ForecastResult:
        request = ForecastRequest.model_validate(request.model_dump() if isinstance(request, ForecastRequest) else request)
        if request.split == "future" and "lightgbm_global_v1" in request.models:
            raise AgentError("no_lightgbm_future", "LightGBM has historical validation/test predictions only. Select an available baseline for forecasts beyond the historical origin.", "refused")
        with gold_session(self.database, self.timeout_seconds) as db:
            source = metadata(db, "fact_forecast")
            validate_filters(db, request)
            bounds = db.execute("SELECT model,min(target_date),max(target_date),max(horizon) FROM fact_forecast WHERE model IN (SELECT unnest(?)) AND split=? GROUP BY model", [list(request.models), request.split]).fetchall()
            if len(bounds) != len(request.models):
                raise AgentError("forecast_unavailable", "One or more selected models have no predictions for that split.", "unavailable")
            start = request.start_date or max(row[1] for row in bounds)
            end = request.end_date or min(row[2] for row in bounds)
            if start > end or any(start < row[1] or end > row[2] or (request.horizon and request.horizon > row[3]) for row in bounds):
                raise AgentError("forecast_period", "The requested target dates or horizon are outside the selected models' available forecast windows.")
            if db.execute("SELECT count(*) FROM fact_forecast WHERE model IN (SELECT unnest(?)) AND split=? AND source_run_id IS DISTINCT FROM ?", [list(request.models), request.split, source.gold_run_id]).fetchone()[0]:
                raise AgentError("stale_forecast", "Forecast lineage does not match the current Gold generation.", "unavailable")
            if db.execute("SELECT count(*) FROM fact_forecast WHERE model IN (SELECT unnest(?)) AND split=? AND ((split='future' AND actual_units IS NOT NULL) OR (split!='future' AND actual_units IS NULL))", [list(request.models), request.split]).fetchone()[0]:
                raise AgentError("forecast_actuals", "The selected split has inconsistent observed/future actuals.", "unavailable")
            group = FORECAST_GROUPS[request.segmentation]
            statement = f"""SELECT model,split,{group} segment,min(target_date),max(target_date),
                min(forecast_origin),max(forecast_origin),count(*),sum(predicted_units),
                CASE WHEN count(actual_units)=count(*) THEN sum(actual_units) END,
                CASE WHEN count(actual_units)=count(*) THEN sum(abs(actual_units-predicted_units))/nullif(sum(abs(actual_units)),0) END,
                CASE WHEN count(actual_units)=count(*) THEN avg(abs(actual_units-predicted_units)) END,
                CASE WHEN count(actual_units)=count(*) THEN sqrt(avg(pow(actual_units-predicted_units,2))) END,
                count(actual_units)=count(*) AND sum(abs(actual_units))=0
                FROM fact_forecast WHERE model IN (SELECT unnest(?)) AND split=?
                AND target_date BETWEEN ? AND ? AND {FILTER_SQL}
                AND (? IS NULL OR horizon=?) AND (? IS NULL OR demand_level=?)
                GROUP BY model,split,segment ORDER BY model,split,segment LIMIT ?"""
            values = [list(request.models), request.split, start, end, *filter_values(request), request.horizon, request.horizon, request.demand_level, request.demand_level, request.limit+1]
            records = bounded_rows(db.execute(statement, values), request.limit)
            rows = [ForecastPoint(model=m, split=s, segment=str(segment), period=Period(start=lo, end=hi), forecast_origin_start=origin_lo, forecast_origin_end=origin_hi,
                                  observations=n, predicted_units=predicted, actual_units=actual, WMAPE=w, MAE=mae, RMSE=rmse, wmape_zero_denominator=bool(zero))
                    for m, s, segment, lo, hi, origin_lo, origin_hi, n, predicted, actual, w, mae, rmse, zero in records]
            warnings = [HISTORICAL, "WMAPE is a ratio of summed absolute errors to summed actual units, never an average of segment percentages. Models are compared separately, never added."]
            if request.split == "future":
                warnings.append("Future means beyond the historical forecast origin, not an operational forecast for today. Actuals and accuracy metrics are unavailable.")
            else:
                warnings.append("Accuracy describes historical backtests, not guaranteed future performance. Demand levels use training-only history.")
            if any(row.wmape_zero_denominator for row in rows):
                warnings.append("WMAPE is undefined because a segment has zero actual units.")
            if not rows:
                warnings.append("No matching forecast observations; no numerical value is available.")
            return ForecastResult(filters=request, rows=rows, provenance=source, warnings=warnings)
