"""Reusable grounded assistant, with deterministic rendering and redacted traces."""
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from retailpulse.agent.contracts import (
    Answer,
    DocsResult,
    ForecastResult,
    KpiResult,
    Trace,
)
from retailpulse.agent.errors import AgentError
from retailpulse.agent.provider import ProviderError
from retailpulse.agent.routing import route


def number(value):
    return "unknown" if value is None else f"{value:,.6f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"


def render(result):
    if isinstance(result, DocsResult):
        lines = ["Approved metric documentation:"]
        for item in result.excerpts:
            lines += [f"{item.source_document}:{item.start_line}-{item.end_line} ({item.section})", "> " + item.excerpt.replace("\n", "\n> ")]
        return "\n".join(lines + result.warnings)
    lines = []
    if isinstance(result, KpiResult):
        for row in result.rows:
            lines.append(f"{result.metric} [{row.segment}]: {number(row.value)} {row.unit}; {row.period.start} to {row.period.end}.")
            if row.previous_period:
                lines.append(f"Previous period {row.previous_period.start} to {row.previous_period.end}: {number(row.previous_value)} units; change {number(row.change)} units ({number(None if row.change_pct is None else row.change_pct*100)}%).")
    elif isinstance(result, ForecastResult):
        for row in result.rows:
            lines.append(f"{row.model}, {row.split}, {row.segment}; {row.period.start} to {row.period.end}: predicted {number(row.predicted_units)} units; observed {number(row.actual_units)} units; WMAPE {number(None if row.WMAPE is None else row.WMAPE*100)}%; MAE {number(row.MAE)} units; RMSE {number(row.RMSE)} units.")
    scope = result.filters.model_dump(mode="json", exclude_none=True)
    scope.pop("limit", None)
    source = result.provenance
    lines += ["Filters: " + json.dumps(scope, sort_keys=True),
              f"Source: Gold {source.source_table}, run {source.gold_run_id}.",
              f"Observed history: {source.observed_period.start} to {source.observed_period.end}. Freshness: {source.data_freshness} days at {source.as_of_date}. Gold generated: {source.generated_at}.",
              *result.warnings]
    return "\n".join(lines)


class Assistant:
    def __init__(self, tools, docs, *, provider=None, provider_status="deterministic", trace_path: Path | None = None):
        self.tools, self.docs, self.provider = tools, docs, provider
        self.provider_status, self.trace_path = provider_status, trace_path

    def ask(self, question: str) -> Answer:
        started, request_id = perf_counter(), str(uuid4())
        plan, result, error, selected = None, None, None, None
        provider = self.provider_status
        try:
            plan = route(question, self.tools.observed_period)
            if self.provider:
                try:
                    plan = self.provider.select(question, plan)
                    # Revalidate even an injected adapter's object; providers cannot supply results.
                    from retailpulse.agent.contracts import Plan
                    verified = Plan.model_validate_json(plan.model_dump_json())
                    expected = route(question, self.tools.observed_period)
                    if verified != expected:
                        raise ProviderError("scope_mismatch")
                    plan = verified
                    provider = "ollama:" + self.provider.model
                except (ProviderError, ValidationError, AttributeError, TypeError):
                    plan = route(question, self.tools.observed_period)
                    provider = "deterministic_fallback:provider_rejected_or_unavailable"
            selected = plan.call.tool
            if selected == "get_kpi":
                result = self.tools.get_kpi(plan.call.arguments)
            elif selected == "get_forecast":
                result = self.tools.get_forecast(plan.call.arguments)
            else:
                result = self.docs.search_metric_docs(plan.call.arguments)
            populated = bool(result.excerpts) if isinstance(result, DocsResult) else bool(result.rows)
            answer = Answer(request_id=request_id, status="answered" if populated else "clarification",
                            answer=render(result), provider=provider, tool=selected, result=result,
                            error_category=None if populated else "no_matching_data", grounding_validated=populated)
        except AgentError as exc:
            error = exc.category
            answer = Answer(request_id=request_id, status=exc.status, answer=str(exc), provider=provider,
                            tool=selected, error_category=error)
        except ValidationError:
            error = "invalid_arguments"
            answer = Answer(request_id=request_id, status="clarification", answer="The requested filters or dates are invalid. Use approved identifiers and an ordered ISO date interval.", provider=provider, tool=selected, error_category=error)
        source = getattr(result, "provenance", None)
        trace = Trace(request_id=request_id, time=datetime.now(UTC), intent_category=selected or error or "clarification",
                      tool=selected, validated_filters=(result.filters.model_dump(mode="json", exclude_none=True) if source else {}),
                      duration_ms=round((perf_counter()-started)*1000, 3), source=source.source_table if source else None,
                      gold_run_id=source.gold_run_id if source else None, outcome=answer.status,
                      error_category=answer.error_category, grounding_validated=answer.grounding_validated, provider=provider)
        if self.trace_path:
            try:
                self.trace_path.parent.mkdir(parents=True, exist_ok=True)
                with self.trace_path.open("a", encoding="utf-8") as stream:
                    stream.write(trace.model_dump_json() + "\n")
            except OSError:
                # Do not return an untraced success when local observability is unavailable.
                return Answer(request_id=request_id, status="error", answer="The local trace could not be recorded. Check the configured trace directory.", provider=provider, error_category="trace_unavailable")
        return answer
