"""Version-aware bounded caching; business calculations stay in RP-09 tools."""

import json
from collections import OrderedDict
from datetime import timedelta
from threading import BoundedSemaphore, Lock
from time import monotonic, perf_counter

from retailpulse.agent.contracts import KpiRequest
from retailpulse.agent.errors import AgentError
from retailpulse.agent.orchestrator import Assistant
from retailpulse.agent.provider import Ollama, ProviderError, detect_ollama
from retailpulse.agent.retrieval import DocSearch
from retailpulse.api.contracts import (
    AssistantResponse,
    ForecastResponse,
    Health,
    ProviderState,
    Summary,
)
from retailpulse.api.source import SYNTHETIC, Source


class Service:
    def __init__(self, settings):
        self.settings, self.source = settings, Source(settings)
        self.cache, self.lock = OrderedDict(), Lock()
        self.slots = BoundedSemaphore(4)
        self.provider_state, self.provider_at = None, 0

    def provider(self):
        if self.provider_state is None or monotonic() - self.provider_at > 5:
            state = detect_ollama()
            self.provider_state = ProviderState(
                available=self.settings.model in state["models"],
                model=self.settings.model,
                default_mode=self.settings.provider,
            )
            self.provider_at = monotonic()
        return self.provider_state

    def health(self):
        try:
            dataset = self.source.describe()
            message = (
                "Historical observations; no live inventory or sales."
                if self.settings.mode == "real"
                else "Explicit synthetic data; illustrative predictions, no trained model claims."
            )
        except AgentError:
            dataset, message = (
                None,
                "Dataset unavailable. Real mode never substitutes synthetic values; use --mode synthetic for a portable demo."
                if self.settings.mode == "real"
                else "The synthetic snapshot is unavailable. Check the packaged demo files and local file access, then restart.",
            )
        return Health(
            status="ok" if dataset else "degraded",
            mode=self.settings.mode,
            dataset_available=dataset is not None,
            dataset=dataset,
            provider=self.provider(),
            message=message,
        )

    def coherent(self, dataset):
        if self.source.describe().dataset_version != dataset.dataset_version:
            raise AgentError(
                "source_changed",
                "The dataset changed during the request; retry for consistent provenance.",
                "unavailable",
            )

    def cached(self, kind, request, build):
        dataset = self.source.describe()
        key = (
            dataset.dataset_version,
            kind,
            json.dumps(request.model_dump(mode="json"), sort_keys=True),
        )
        with self.lock:
            # Discard other generations, not merely their key references.
            for old in list(self.cache):
                if (
                    old[0] != dataset.dataset_version
                    or monotonic() - self.cache[old][0] > 60
                ):
                    del self.cache[old]
            entry = self.cache.get(key)
        if entry:
            self.coherent(dataset)
            return entry[1].model_copy(deep=True, update={"cached": True})
        result = build(dataset)
        self.coherent(dataset)
        with self.lock:
            self.cache[key] = (monotonic(), result.model_copy(deep=True))
            while len(self.cache) > 32:
                self.cache.popitem(last=False)
        return result

    def summary(self, request):
        # Normalize omitted date bounds before caching.
        dataset = self.source.describe()
        request = request.model_copy(
            update={
                "start_date": request.start_date
                or dataset.lineage.observed_period.start,
                "end_date": request.end_date or dataset.lineage.observed_period.end,
            }
        )

        def build(dataset):
            deadline = monotonic() + 12
            scope = request.model_dump(exclude_none=True)

            def kpi(metric, **kwargs):
                if monotonic() > deadline:
                    raise AgentError(
                        "query_timeout",
                        "The summary exceeded its budget. Narrow the selected period.",
                        "unavailable",
                    )
                return self.source.tools.get_kpi(
                    KpiRequest(metric=metric, **{**scope, **kwargs})
                )

            metrics = {
                m: kpi(m)
                for m in (
                    "units",
                    "price_coverage",
                    "known_revenue_proxy",
                    "revenue_proxy",
                    "demand_spike_flag",
                )
            }
            trend = kpi(
                "units",
                start_date=max(
                    request.start_date, request.end_date - timedelta(days=89)
                ),
                granularity="day",
            )
            return Summary(
                dataset=dataset,
                filters=request,
                metrics=metrics,
                daily_trend=trend,
                stores=kpi("units", granularity="store"),
                departments=kpi("units", granularity="department"),
            )

        return self.cached("summary", request, build)

    def forecast(self, request):
        return self.cached(
            "forecast",
            request,
            lambda dataset: ForecastResponse(
                dataset=dataset, result=self.source.tools.get_forecast(request)
            ),
        )

    def ask(self, request):
        dataset = self.source.describe()
        provider, discovery = None, None
        label = "deterministic:explicit_offline_mode"
        if request.provider != "deterministic":
            if self.provider().available:
                provider = Ollama(self.settings.model)
                label = "ollama:" + self.settings.model
            else:
                discovery = ProviderError("model_unavailable").diagnostic
                label = "deterministic_fallback:ollama_or_selected_model_unavailable"
        docs = DocSearch(
            SYNTHETIC if self.settings.mode == "synthetic" else self.settings.root
        )
        assistant = Assistant(
            self.source.tools,
            docs,
            provider=provider,
            provider_status=label,
            discovery_diagnostic=discovery,
            trace_path=self.settings.root
            / "artifacts/web_demo"
            / self.settings.mode
            / "traces.jsonl",
        )
        started = perf_counter()
        result = assistant.ask(request.question)
        self.coherent(dataset)
        return AssistantResponse(
            dataset=dataset,
            result=result,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            live_provider_succeeded=result.provider_diagnostic.status == "succeeded"
            and result.provider.startswith("ollama:"),
        )
