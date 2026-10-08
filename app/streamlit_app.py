"""Bilingual local portfolio UI. Typed API tools own all business values."""

import os
from datetime import date, datetime
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from retailpulse.api.client import ApiClient, ApiClientError
from retailpulse.ui.answers import MODELS, Presentation, answer_card, forecast_cards
from retailpulse.ui.i18n import date_label, period_label
from retailpulse.ui.theme import PALETTES, chart_style, css

API = os.environ.get("RETAILPULSE_API_URL", "http://127.0.0.1:8000")
ROOT = Path(os.environ.get("RETAILPULSE_ROOT", Path(__file__).resolve().parents[1]))


def present():
    return Presentation(st.session_state.get("language", "en"))


def t(text, **values):
    return present().t(text, **values)


def palette():
    return PALETTES[st.session_state.get("theme", "light")]


def chart(chart, height):
    st.altair_chart(
        chart_style(chart, st.session_state.get("theme", "light"), present().language),
        width="stretch",
        height=height,
        theme=None,
    )


def points(result):
    p = present()
    return pd.DataFrame(
        [
            {
                "Date": r["period"]["start"],
                "Units": r["value"],
                "Segment": r["segment"],
                "DisplayDate": date_label(r["period"]["start"], p.language),
                "DisplayValue": p.n(r["value"]),
            }
            for r in result["rows"]
        ]
    )


def provenance(dataset):
    p = present()
    source = dataset["lineage"]
    st.caption(
        t(
            "Observed {period} · Snapshot: {as_of}",
            period=period_label(source["observed_period"], p.language),
            as_of=date_label(source["as_of_date"], p.language),
        )
    )


def overview(client, dataset, scope):
    p = present()
    st.subheader(t("The demand picture"))
    st.caption(
        t("Observed sales, transparent price coverage and signals worth investigating.")
    )
    result = client.request("/metrics/summary", params=scope)
    metrics = result["metrics"]

    def value(key):
        rows = metrics[key]["rows"]
        return rows[0]["value"] if rows else None

    for col, key, label in zip(
        st.columns([1, 1, 1.55, 1.2, 1]),
        (
            "units",
            "price_coverage",
            "known_revenue_proxy",
            "demand_spike_flag",
            "data_freshness",
        ),
        (
            "Observed units",
            "Price coverage",
            "Known-price revenue proxy",
            "Demand spike flags",
            "Historical freshness",
        ),
        strict=True,
    ):
        number = (
            dataset["lineage"]["data_freshness"]
            if key == "data_freshness"
            else value(key)
        )
        col.metric(t(label), p.metric_value(key, number), border=True)
    revenue = metrics["revenue_proxy"]["rows"]
    if revenue and revenue[0]["value"] is None:
        st.caption(
            t(
                "Partial proxy: {count} observations lack prices. Complete revenue is unknown; this is not audited revenue.",
                count=p.n(revenue[0]["missing_observations"]),
            )
        )
    else:
        st.caption(
            t(
                "Revenue is a price-based proxy, not audited revenue. Spike flags do not prove stockouts or causes."
            )
        )
    st.markdown("#### " + t("Daily demand"))
    st.caption(
        t(
            "Last 90 days of the selected range; cards and comparisons use the entire range."
        )
    )
    frame = points(result["daily_trend"])
    if not frame.empty:
        chart(
            alt.Chart(frame)
            .mark_area(
                color=palette()["accent"],
                opacity=0.18,
                line={"color": palette()["accent"], "strokeWidth": 2.5},
            )
            .encode(
                x=alt.X(
                    "Date:T",
                    title=None,
                    axis=alt.Axis(format="%d/%m" if p.language == "es" else "%b %d"),
                ),
                y=alt.Y(
                    "Units:Q", title=t("Observed units"), axis=alt.Axis(format=",.0f")
                ),
                tooltip=[
                    alt.Tooltip("DisplayDate:N", title=t("Date")),
                    alt.Tooltip("DisplayValue:N", title=t("Units")),
                ],
            ),
            255,
        )
    for col, label, key in zip(
        st.columns(2),
        ("By store", "By department"),
        ("stores", "departments"),
        strict=True,
    ):
        with col:
            st.markdown("#### " + t(label))
            frame = points(result[key])
            if not frame.empty:
                chart(
                    alt.Chart(frame)
                    .mark_bar(color=palette()["blue"], cornerRadiusEnd=4)
                    .encode(
                        x=alt.X(
                            "Units:Q",
                            title=t("Observed units"),
                            axis=alt.Axis(format=",.0f"),
                        ),
                        y=alt.Y("Segment:N", title=None, sort="-x"),
                        tooltip=[
                            alt.Tooltip("Segment:N", title=t("Segment")),
                            alt.Tooltip("DisplayValue:N", title=t("Units")),
                        ],
                    ),
                    155,
                )
    with st.expander(t("Source & metric definitions")):
        st.json(
            {
                "dataset": dataset,
                "filters": result["filters"],
                "metrics": {k: v["provenance"] for k, v in metrics.items()},
                "cached": result["cached"],
            }
        )


def forecast(client, dataset, scope):
    p = present()
    st.subheader(t("Forecasts with an honest scorecard"))
    st.info(
        t(
            "Full-pilot historical test: LightGBM improves WMAPE and MAE, but has worse RMSE than rolling mean. Filtered segments can differ. No future LightGBM forecast is available."
            if dataset["mode"] == "real"
            else "Synthetic comparison: the LightGBM series is simulated, not trained. These scores do not measure real model performance."
        )
    )
    a, b, c = st.columns([2, 1, 1])
    with a:
        models = st.multiselect(
            t("Models to compare"),
            list(MODELS),
            default=st.session_state.get(
                "models", ["lightgbm_global_v1", "rolling_mean"]
            ),
            format_func=lambda m: p.t(MODELS[m]),
            max_selections=2,
            placeholder=t("Models to compare"),
            key="models_" + p.language,
        )
    with b:
        split = st.selectbox(
            t("Historical split"),
            ["test", "validation"],
            format_func=lambda s: p.t(s.title()),
            index=["test", "validation"].index(st.session_state.get("split") or "test"),
            key="split_" + p.language,
        )
    windows = [
        w
        for w in dataset["forecast_windows"]
        if w["model"] in models and w["split"] == split
    ]
    with c:
        maximum = min((w["max_horizon"] for w in windows), default=1)
        horizon = st.selectbox(
            t("Forecast horizon"),
            [None, *range(1, maximum + 1)],
            format_func=lambda n: (
                p.t("All horizons") if n is None else p.t("Day {n}", n=n)
            ),
            index=(
                [None, *range(1, maximum + 1)].index(st.session_state.get("horizon"))
                if st.session_state.get("horizon") in [None, *range(1, maximum + 1)]
                else 0
            ),
            key="horizon_" + p.language,
            placeholder=t("All horizons"),
        )
    st.session_state.update(models=models, split=split, horizon=horizon)
    st.caption(
        t(
            "Store and department filters apply here. Sales dates apply to Overview; forecasts use the selected historical split."
        )
    )
    if not models:
        st.info(t("Choose a model to view historical performance."))
        return
    params = (
        [(k, v) for k, v in scope.items() if k in ("store", "department")]
        + [("models", m) for m in models]
        + [("split", split)]
    )
    if horizon:
        params.append(("horizon", horizon))
    response = client.request("/forecast", params=params)
    result = response["result"]
    rows = result["rows"]
    forecast_cards(rows, p)
    if not rows:
        return
    daily = client.request("/forecast", params=params + [("segmentation", "day")])[
        "result"
    ]["rows"]
    frame = []
    for row in daily:
        frame.append(
            {
                "Date": row["period"]["start"],
                "Units": row["predicted_units"],
                "Series": t(MODELS[row["model"]]),
            }
        )
        if row["model"] == rows[0]["model"]:
            frame.append(
                {
                    "Date": row["period"]["start"],
                    "Units": row["actual_units"],
                    "Series": t("Observed actuals"),
                }
            )
    for row in frame:
        row.update(
            DisplayDate=date_label(row["Date"], p.language),
            DisplayValue=p.n(row["Units"], 2),
        )
    st.markdown("#### " + t("Observed vs predicted demand"))
    chart(
        alt.Chart(pd.DataFrame(frame))
        .mark_line(strokeWidth=2.5, point=True)
        .encode(
            x=alt.X(
                "Date:T",
                title=None,
                axis=alt.Axis(format="%d/%m" if p.language == "es" else "%b %d"),
            ),
            y=alt.Y("Units:Q", title=t("Daily units"), axis=alt.Axis(format=",.0f")),
            color=alt.Color(
                "Series:N",
                title=None,
                scale=alt.Scale(
                    range=[palette()["accent"], palette()["blue"], palette()["amber"]]
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("DisplayDate:N", title=t("Date")),
                alt.Tooltip("Series:N", title=t("Series")),
                alt.Tooltip("DisplayValue:N", title=t("Units")),
            ],
        ),
        285,
    )
    st.caption(
        t(
            "Accuracy describes historical backtests. Each model is compared separately; predictions are never added across models."
        )
    )
    with st.expander(t("Forecast scope & provenance")):
        st.json(response)


def example_questions(dataset, language):
    p = Presentation(language)
    period = dataset["lineage"]["observed_period"]
    demand = (
        p.t("How many units did CA_1 sell during April 2016?")
        if dataset["mode"] == "real"
        else p.t(
            "Show units for {store} from {start} to {end}",
            store=dataset["stores"][0],
            start=period["start"],
            end=period["end"],
        )
    )
    return [
        demand,
        p.t("Compare LightGBM and rolling mean WMAPE on the test period"),
        p.t("What does revenue_proxy mean?"),
        p.t("How old is the data?"),
    ]


def assistant(client, health):
    p = present()
    st.subheader(t("Ask RetailPulse"))
    st.caption(t("One clear question. Approved tools. Verifiable answers."))
    provider = st.radio(
        t("Answer provider"),
        ["ollama", "deterministic"],
        index=1
        if (st.session_state.get("provider") or health["provider"]["default_mode"])
        == "deterministic"
        else 0,
        format_func=lambda mode: p.t(
            "Ollama · local model" if mode == "ollama" else "Deterministic · offline"
        ),
        horizontal=True,
        key="provider_" + p.language,
    )
    st.session_state["provider"] = provider
    if provider == "ollama" and not health["provider"]["available"]:
        st.warning(
            t(
                "Ollama is unavailable. Start the local service or choose deterministic mode. Any fallback is explicitly disclosed."
            )
        )
    pending = None
    for col, title, question in zip(
        st.columns(4),
        (
            "Explore store demand",
            "Compare forecast models",
            "Explain revenue proxy",
            "Check data freshness",
        ),
        example_questions(health["dataset"], present().language),
        strict=True,
    ):
        if col.button(t(title), width="stretch", key="example_" + title):
            pending = question
    st.caption(
        t(
            "Each question is independent. Chat history is not sent to the assistant. Spanish support is limited to the suggested forms and explicit store/month or ISO date ranges."
        )
    )
    history = st.session_state.setdefault("rp_chat", [])
    for exchange in history:
        with st.chat_message("user", avatar=":material/person:"):
            st.write(exchange["question"])
        with st.chat_message("assistant", avatar=":material/analytics:"):
            answer_card(exchange["response"], present().language)
    pending = (
        st.chat_input(
            t("Ask about historical units, metrics or forecast accuracy"),
            max_chars=1000,
            key="question",
        )
        or pending
    )
    if pending:
        with st.chat_message("user", avatar=":material/person:"):
            st.write(pending)
        with st.chat_message("assistant", avatar=":material/analytics:"):
            with st.spinner(
                t(
                    "Consulting approved tools. A cold local model may take up to 30 seconds."
                )
            ):
                response = client.request(
                    "/assistant/query", body={"question": pending, "provider": provider}
                )
            answer_card(response, present().language)
        history.append({"question": pending, "response": response})
        del history[:-8]


def architecture(dataset):
    st.subheader(t("Trace every answer back to its source"))
    st.caption(
        t(
            "A local analytical product, from observations to a grounded business answer."
        )
    )
    blocks = []
    for number, title, label, description in zip(
        ("01", "02", "03", "04"),
        ("M5 → Bronze", "Silver", "Gold / DuckDB", "Forecasting / MLflow"),
        ("Source data", "Validated data", "Business metrics", "Models & decisions"),
        (
            "M5 CSV inputs, content hashes and immutable ingestion provenance.",
            "Validated daily sales, calendar and prices; explicit missing data.",
            "Canonical KPIs and read-only analytical tools, with source lineage.",
            "Frozen forecasting / MLflow → Power BI, FastAPI, Streamlit and the grounded assistant.",
        ),
        strict=True,
    ):
        blocks.append(
            f'<article class="rp-stage"><small>{number} / {escape(t(label))}</small><h4>{escape(title)}</h4><p>{escape(t(description))}</p></article>'
        )
    st.markdown(
        '<div class="rp-pipeline">' + "".join(blocks) + "</div>", unsafe_allow_html=True
    )
    left, right = st.columns(2)
    with left:
        st.markdown("#### " + t("Built to be checked"))
        st.write(
            t(
                "Synthetic tests run without Kaggle or Ollama. Real acceptance reconciles API results with Gold. Frozen artifacts and source hashes are preserved."
            )
        )
        st.link_button(
            t("Explore the metric catalog"),
            "https://github.com/sjimenezch001/retailpulse-ai/blob/main/docs/metric_catalog.md",
        )
        st.link_button(t("Open the API documentation"), API + "/docs")
    with right:
        st.markdown("#### " + t("Know the limits"))
        st.write(
            t(
                "Historical data is not current sales. M5 has no inventory data. Revenue is a proxy; spikes are heuristic. No AWS deployment is claimed."
            )
        )
        st.link_button(
            t("Read the model card"),
            "https://github.com/sjimenezch001/retailpulse-ai/blob/main/docs/model_card.md",
        )
        guide = ROOT / "docs/web_demo.md"
        if guide.is_file():
            st.download_button(
                t("Download the demo guide"),
                guide.read_text(encoding="utf-8"),
                file_name="RetailPulse-demo-guide.md",
                mime="text/markdown",
            )
    st.caption(t("Documentation is maintained in English."))
    with st.expander(t("Dataset lineage")):
        st.json(dataset)


def date_filters(dataset):
    """Locale-controlled date input avoids browser-locale calendar text."""
    lang = present().language
    period = dataset["lineage"]["observed_period"]
    canonical = st.session_state.setdefault(
        "sales_dates",
        (date.fromisoformat(period["start"]), date.fromisoformat(period["end"])),
    )
    fmt = "%d/%m/%Y" if lang == "es" else "%m/%d/%Y"
    if st.session_state.get("date_language") != lang:
        st.session_state["date_start"] = canonical[0].strftime(fmt)
        st.session_state["date_end"] = canonical[1].strftime(fmt)
        st.session_state["date_language"] = lang
    help_text = t(
        "Use {format}.", format="DD/MM/YYYY" if lang == "es" else "MM/DD/YYYY"
    )
    start = st.text_input(t("Start date"), key="date_start", help=help_text)
    end = st.text_input(t("End date"), key="date_end", help=help_text)
    try:
        dates = (
            datetime.strptime(start, fmt).date(),
            datetime.strptime(end, fmt).date(),
        )
        if (
            not date.fromisoformat(period["start"])
            <= dates[0]
            <= dates[1]
            <= date.fromisoformat(period["end"])
        ):
            raise ValueError
    except ValueError:
        st.warning(t("Use valid, ordered dates within the observed period."))
        return None
    st.session_state["sales_dates"] = dates
    return dates


def main():
    st.session_state.setdefault("language", "en")
    st.session_state.setdefault("theme", "light")
    st.set_page_config(page_title="RetailPulse AI", page_icon="◈", layout="wide")
    brand, language, theme = st.columns([6, 1.4, 1.2])
    with language:
        st.selectbox(
            "Language / Idioma",
            ["en", "es"],
            format_func=lambda lang: "English" if lang == "en" else "Español",
            key="language",
        )
    with theme:
        p = present()
        chosen_theme = st.selectbox(
            t("Theme"),
            ["light", "dark"],
            index=["light", "dark"].index(st.session_state["theme"]),
            format_func=lambda value: p.t(value.title()),
            key="theme_" + p.language,
        )
        st.session_state["theme"] = chosen_theme
    st.markdown(css(st.session_state["theme"]), unsafe_allow_html=True)
    with brand:
        st.markdown(
            '<div class="rp-eyebrow">RETAILPULSE AI / '
            + escape(t("DEMAND INTELLIGENCE"))
            + "</div>",
            unsafe_allow_html=True,
        )
    st.title(t("See demand. Understand the evidence."))
    st.caption(t("Retail analytics, honest forecasts and answers you can trace."))
    client = ApiClient(API)
    try:
        health = client.request("/health")
    except ApiClientError:
        st.error(
            t("The local API is unavailable or timed out. Start the demo and retry.")
        )
        st.code("python -m retailpulse demo", language="powershell")
        return
    dataset = health["dataset"]
    if not dataset:
        st.warning(
            t(
                "The real dataset is unavailable. Choose explicit synthetic mode for the portable demo."
                if health["mode"] == "real"
                else "The synthetic snapshot is unavailable. Check the local demo files and restart."
            )
        )
        st.code(
            "python -m retailpulse demo --mode synthetic --provider deterministic",
            language="powershell",
        )
        return
    if st.session_state.get("rp_version") != dataset["dataset_version"]:
        for key in ("rp_chat", "sales_dates", "date_language", "store", "department"):
            st.session_state.pop(key, None)
        st.session_state["rp_version"] = dataset["dataset_version"]
    if dataset["mode"] == "synthetic":
        st.warning(
            t(
                "SYNTHETIC PORTFOLIO DEMO · All observations and comparison series are illustrative. No real M5 data or trained-model performance."
            )
        )
    else:
        st.caption(t("REAL M5 · HISTORICAL PILOT · Local and read-only"))
    provenance(dataset)
    with st.sidebar:
        st.markdown("### " + t("Your analysis scope"))
        st.caption(t(dataset["label"]))
        dates = date_filters(dataset)
        store = st.selectbox(
            t("Store"),
            [None, *dataset["stores"]],
            format_func=lambda s: s or p.t("All stores"),
            key="store",
            placeholder=t("All stores"),
        )
        department = st.selectbox(
            t("Department"),
            [None, *dataset["departments"]],
            format_func=lambda s: s or p.t("All departments"),
            key="department",
            placeholder=t("All departments"),
        )
        st.divider()
        st.markdown("**" + t("Snapshot freshness") + "**")
        st.write(
            t("{value} days", value=present().n(dataset["lineage"]["data_freshness"]))
        )
        st.caption(
            t(
                "Measured at {date}; not pipeline latency.",
                date=date_label(dataset["lineage"]["as_of_date"], present().language),
            )
        )
        st.caption(t("No current sales or inventory claims."))
    if dates is None:
        return
    scope = {"start_date": str(dates[0]), "end_date": str(dates[1])}
    if store:
        scope["store"] = store
    if department:
        scope["department"] = department
    tabs = st.tabs(
        [
            t(name)
            for name in ("Overview", "Forecast", "Ask RetailPulse", "Architecture")
        ],
        key="navigation",
    )
    for tab, function, args in zip(
        tabs,
        (overview, forecast, assistant, architecture),
        (
            (client, dataset, scope),
            (client, dataset, scope),
            (client, health),
            (dataset,),
        ),
        strict=True,
    ):
        with tab:
            try:
                function(*args)
            except ApiClientError:
                st.error(
                    t(
                        "The request could not be completed. Check the filters or retry shortly."
                    )
                )
    st.caption(
        "RetailPulse AI · "
        + t("Historical evidence · Reproducible results · Local portfolio demo")
    )


if __name__ == "__main__":
    main()
