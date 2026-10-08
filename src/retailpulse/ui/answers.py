"""Readable answers derived exclusively from the typed, grounded API result."""

from html import escape

import streamlit as st

from retailpulse.ui.i18n import EXCERPT_ES, date_label, number, period_label, translate

METRIC_LABELS = {
    "units": "Observed units",
    "revenue_proxy": "Revenue proxy",
    "known_revenue_proxy": "Known-price revenue proxy",
    "price_coverage": "Price coverage",
    "data_freshness": "Historical freshness",
    "demand_spike_flag": "Demand spike flags",
    "rolling_7d": "7-day rolling demand",
    "rolling_28d": "28-day rolling demand",
    "price_change_pct": "Price change",
}
MODELS = {
    "lightgbm_global_v1": "LightGBM",
    "rolling_mean": "Rolling mean",
    "last_value": "Last value",
    "seasonal_naive_7": "Seasonal naive (7)",
}
ERROR_COPY = {
    "current_period": "This snapshot contains historical observations, not current sales.",
    "no_inventory": "Inventory data is unavailable; zero sales do not establish a stockout.",
    "no_causal_evidence": "These observations do not establish causation.",
}
# Exact, reviewed source translations. Changed/unrecognized excerpts remain
# explicitly labeled original quotations, never generated or guessed summaries.


class Presentation:
    def __init__(self, language="en"):
        self.language = language

    def t(self, text, **values):
        return translate(text, self.language, **values)

    def n(self, value, decimals=0):
        return number(value, self.language, decimals)

    def metric_value(self, metric, value):
        if value is None:
            return self.t("Unknown")
        if metric == "price_coverage":
            return self.n(value * 100, 2) + "%"
        if metric == "data_freshness":
            return self.t("{value} days", value=self.n(value))
        return self.n(
            value,
            2
            if metric
            in {
                "revenue_proxy",
                "known_revenue_proxy",
                "rolling_7d",
                "rolling_28d",
                "price_change_pct",
            }
            else 0,
        )

    def kpi_sentence(self, result, row):
        value = self.metric_value(result["metric"], row["value"])
        period = period_label(row["period"], self.language)
        filters = result["filters"]
        if result["metric"] == "units" and row["value"] is not None:
            if (
                filters.get("store")
                and not filters.get("department")
                and not filters.get("item")
                and filters.get("granularity") == "total"
            ):
                return self.t(
                    "Store {store} sold {value} units during {period}.",
                    store=filters["store"],
                    value=value,
                    period=period,
                )
            return self.t(
                "The selected scope recorded {value} units during {period}.",
                value=value,
                period=period,
            )
        if result["metric"] == "data_freshness":
            return self.t(
                "Data is {value} days old at the snapshot date {date}.",
                value=self.n(row["value"]),
                date=date_label(result["provenance"]["as_of_date"], self.language),
            )
        return self.t(
            "{metric}: {value} for the selected scope.",
            metric=self.t(METRIC_LABELS[result["metric"]]),
            value=value,
        )


def table(headers, rows):
    head = "".join(f'<th scope="col">{escape(str(h))}</th>' for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="rp-table-wrap"><table class="rp-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def scope_caption(result, p):
    filters = result["filters"]
    selected = [
        p.t(label) + ": " + str(filters[key])
        for key, label in (
            ("store", "Store"),
            ("department", "Department"),
            ("item", "Item"),
        )
        if filters.get(key)
    ]
    st.caption(" · ".join(selected) or p.t("All selected observations"))


def forecast_cards(rows, p):
    if not rows:
        st.info(p.t("No predictions match the selected scope."))
        return
    if len(rows) > 4:
        table(
            [p.t(k) for k in ("Forecast", "Segment", "Period", "WMAPE", "MAE", "RMSE")],
            [
                [
                    p.t(MODELS[r["model"]]),
                    r["segment"],
                    period_label(r["period"], p.language),
                    p.t("Undefined")
                    if r["WMAPE"] is None
                    else p.n(r["WMAPE"] * 100, 2) + "%",
                    p.n(r["MAE"], 3),
                    p.n(r["RMSE"], 3),
                ]
                for r in rows
            ],
        )
        return
    for column, row in zip(st.columns(len(rows)), rows, strict=True):
        with column:
            st.markdown("#### " + p.t(MODELS[row["model"]]))
            st.caption(
                p.t(row["split"].title())
                + " · "
                + period_label(row["period"], p.language)
            )
            if row["segment"] not in {"all", "overall"}:
                st.caption(p.t("Segment") + ": " + row["segment"])
            for col, key, help_text in zip(
                st.columns(3),
                ("WMAPE", "MAE", "RMSE"),
                (
                    "Weighted absolute error as a share of observed units; lower is better.",
                    "Average absolute error in units; lower is better.",
                    "Root mean squared error in units; more sensitive to large errors.",
                ),
                strict=True,
            ):
                displayed = (
                    p.t("Undefined")
                    if row[key] is None
                    else p.n(row[key] * 100, 2) + "%"
                    if key == "WMAPE"
                    else p.n(row[key], 3)
                )
                col.metric(key, displayed, help=p.t(help_text), border=True)
    if (
        len(rows) == 2
        and rows[0]["period"] == rows[1]["period"]
        and rows[0]["segment"] == rows[1]["segment"]
    ):
        by_model = {r["model"]: r for r in rows}
        ml, baseline = by_model.get("lightgbm_global_v1"), by_model.get("rolling_mean")
        if (
            ml
            and baseline
            and all(r[k] is not None for r in rows for k in ("WMAPE", "MAE", "RMSE"))
        ):
            tradeoff = (
                ml["WMAPE"] < baseline["WMAPE"]
                and ml["MAE"] < baseline["MAE"]
                and ml["RMSE"] > baseline["RMSE"]
            )
            st.caption(
                p.t(
                    "This scope has lower LightGBM WMAPE and MAE, but higher RMSE than rolling mean."
                    if tradeoff
                    else "Compare each error measure; the results do not establish a universal winner."
                )
            )


def answer_card(response, language="en"):
    p = Presentation(language)
    answer = response["result"]
    result = answer.get("result")
    grounded = (
        answer["status"] == "answered"
        and answer["grounding_validated"]
        and result is not None
    )
    if not grounded:
        copy = ERROR_COPY.get(answer.get("error_category")) or {
            "clarification": "Please clarify the metric, observed period and scope. Try one of the supported example questions.",
            "refused": "This request is outside the approved read-only analytical tools. Choose a supported historical question.",
            "unavailable": "The requested data is unavailable. Check the local demo service and selected scope.",
        }.get(
            answer["status"],
            "The answer could not be completed safely. Please retry or use a supported example.",
        )
        st.warning(p.t(copy))
    elif result["tool"] == "get_kpi":
        rows = result["rows"]
        if len(rows) == 1:
            row = rows[0]
            st.write(p.kpi_sentence(result, row))
            # A compact card makes the answer, not its transport metadata, primary.
            col, _ = st.columns([2, 3])
            col.metric(
                p.t(METRIC_LABELS[result["metric"]]),
                p.metric_value(result["metric"], row["value"]),
                border=True,
            )
            st.caption(p.t("Period") + ": " + period_label(row["period"], language))
            if row.get("previous_period"):
                st.caption(
                    p.t("Previous period")
                    + ": "
                    + period_label(row["previous_period"], language)
                    + " · "
                    + p.n(row["previous_value"])
                    + " "
                    + p.t("units")
                    + " · "
                    + p.t("Change")
                    + ": "
                    + p.n(row["change"])
                )
        else:
            table(
                [p.t("Segment"), p.t(METRIC_LABELS[result["metric"]]), p.t("Period")],
                [
                    [
                        r["segment"],
                        p.metric_value(result["metric"], r["value"]),
                        period_label(r["period"], language),
                    ]
                    for r in rows
                ],
            )
        scope_caption(result, p)
        missing = sum(row.get("missing_observations", 0) for row in rows)
        if result["metric"] in {"revenue_proxy", "known_revenue_proxy"}:
            st.caption(
                p.t(
                    "Revenue is a price-based proxy, not audited revenue. Spike flags do not prove stockouts or causes."
                )
            )
            if missing:
                st.info(
                    p.t(
                        "Partial proxy: {count} observations lack prices. Complete revenue is unknown; this is not audited revenue.",
                        count=p.n(missing),
                    )
                )
    elif result["tool"] == "get_forecast":
        st.write(p.t("Historical forecast comparison"))
        forecast_cards(result["rows"], p)
        scope_caption(result, p)
        st.caption(
            p.t(
                "Accuracy describes historical backtests. Each model is compared separately; predictions are never added across models."
            )
        )
    elif result["tool"] == "search_metric_docs":
        st.write(p.t("From the approved metric documentation"))
        for excerpt in result["excerpts"]:
            st.caption(
                f"{excerpt['source_document']} · {p.t('lines')} {excerpt['start_line']}–{excerpt['end_line']}"
            )
            translated = (
                EXCERPT_ES.get(excerpt["excerpt"]) if language == "es" else None
            )
            if translated:
                st.markdown(translated)
                with st.expander(p.t("Original source excerpt (English)")):
                    st.text(excerpt["excerpt"])
            else:
                if language == "es":
                    st.caption(
                        p.t(
                            "This is an original, unmodified source excerpt. Repository documents remain in English."
                        )
                    )
                st.markdown("> " + excerpt["excerpt"].replace("\n", "\n> "))
    if result and result.get("provenance"):
        source = result["provenance"]
        st.caption(
            p.t("Source")
            + ": Gold · "
            + source["source_table"]
            + " · "
            + source["gold_run_id"]
        )
    st.caption(
        ("✓ " if grounded else "○ ")
        + p.t("Grounded in approved data" if grounded else "Grounding not validated")
    )
    if answer["provider"].startswith("deterministic_fallback"):
        st.warning(
            p.t("Deterministic fallback")
            + " · "
            + p.t(
                "The local model did not complete this answer. Approved deterministic tools provided the result."
            )
        )
    label = (
        p.t("Live local model")
        if response["live_provider_succeeded"]
        else p.t("Deterministic · offline")
        if answer["provider"] == "deterministic:explicit_offline_mode"
        else p.t("Deterministic fallback")
        if answer["provider"].startswith("deterministic_fallback")
        else p.t("Local model not called")
    )
    st.caption(
        f"{label} · {answer['provider']} · {p.n(response['latency_ms'] / 1000, 2)} s"
    )
    with st.expander(p.t("Sources, scope & provider diagnostics")):
        st.json(response)
