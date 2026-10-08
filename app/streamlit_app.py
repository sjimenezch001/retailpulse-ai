"""RetailPulse portfolio UI: presentation only; all figures arrive through the API."""

import os
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from retailpulse.api.client import ApiClient, ApiClientError

API = os.environ.get("RETAILPULSE_API_URL", "http://127.0.0.1:8000")
ROOT = Path(os.environ.get("RETAILPULSE_ROOT", Path(__file__).resolve().parents[1]))
MODEL_LABELS = {
    "lightgbm_global_v1": "LightGBM",
    "rolling_mean": "Rolling mean",
    "last_value": "Last value",
    "seasonal_naive_7": "Seasonal naive (7)",
}


def value(result):
    return result["rows"][0]["value"] if result["rows"] else None


def formatted(number, decimals=0):
    return "Unknown" if number is None else f"{number:,.{decimals}f}"


def chart_rows(result):
    return pd.DataFrame(
        [
            {
                "Date": row["period"]["start"],
                "Units": row["value"],
                "Segment": row["segment"],
            }
            for row in result["rows"]
        ]
    )


def provenance(dataset):
    lineage = dataset["lineage"]
    st.caption(
        f"{dataset['label']} · observed {lineage['observed_period']['start']}–{lineage['observed_period']['end']} · snapshot as of {lineage['as_of_date']}"
    )


def overview(client, dataset, scope):
    st.subheader("The demand picture")
    st.caption(
        "Observed sales, transparent price coverage and signals worth investigating."
    )
    result = client.request("/metrics/summary", params=scope)
    metrics = result["metrics"]
    columns = st.columns(5)
    cards = [
        ("Observed units", formatted(value(metrics["units"]))),
        (
            "Price coverage",
            f"{value(metrics['price_coverage']) * 100:.2f}%"
            if value(metrics["price_coverage"]) is not None
            else "Unknown",
        ),
        (
            "Known-price revenue proxy",
            formatted(value(metrics["known_revenue_proxy"]), 2),
        ),
        ("Demand spike flags", formatted(value(metrics["demand_spike_flag"]))),
        ("Historical freshness", f"{dataset['lineage']['data_freshness']:,} days"),
    ]
    for column, (label, number) in zip(columns, cards, strict=True):
        column.metric(label, number, border=True)
    revenue = metrics["revenue_proxy"]["rows"]
    if revenue and revenue[0]["value"] is None:
        st.info(
            f"Known-price revenue is a partial proxy. {revenue[0]['missing_observations']:,} selected observations lack prices, so the complete revenue proxy is unknown. This is not audited revenue."
        )
    else:
        st.caption(
            "Known-price revenue is a price-based proxy, not audited revenue. Spike flags are heuristic, not evidence of stockouts or causes."
        )
    frame = chart_rows(result["daily_trend"])
    st.markdown("#### Daily demand")
    st.caption(
        "Daily sums for up to the last 90 observed days in the selected range. KPI cards and comparisons use the entire selected range."
    )
    if not frame.empty:
        chart = (
            alt.Chart(frame)
            .mark_area(
                color="#168494",
                opacity=0.2,
                line={"color": "#168494", "strokeWidth": 2.5},
            )
            .encode(
                x=alt.X("Date:T", title=None),
                y=alt.Y("Units:Q", title="Observed units"),
                tooltip=["Date:T", "Units:Q"],
            )
        )
        st.altair_chart(chart, width="stretch", height=270)
    left, right = st.columns(2)
    for column, title, key in (
        (left, "By store", "stores"),
        (right, "By department", "departments"),
    ):
        with column:
            st.markdown(f"#### {title}")
            frame = chart_rows(result[key])
            if not frame.empty:
                chart = (
                    alt.Chart(frame)
                    .mark_bar(color="#253F66", cornerRadiusEnd=4)
                    .encode(
                        x=alt.X("Units:Q", title="Observed units"),
                        y=alt.Y("Segment:N", title=None, sort="-x"),
                        tooltip=["Segment", "Units"],
                    )
                )
                st.altair_chart(chart, width="stretch", height=175)
    with st.expander("Source & metric definitions"):
        st.json(
            {
                "dataset_version": dataset["dataset_version"],
                "filters": result["filters"],
                "provenance": metrics["units"]["provenance"],
                "cached": result["cached"],
            }
        )


def forecast(client, dataset, scope):
    st.subheader("Forecasts with an honest scorecard")
    if dataset["mode"] == "real":
        st.info(
            "Full-pilot historical test: LightGBM improves WMAPE and MAE, but has worse RMSE than rolling mean. Filtered segments can differ. No operational future LightGBM forecast is available."
        )
    else:
        st.info(
            "Synthetic demonstration: the LightGBM comparison series is simulated, not trained. These scores illustrate the interface and do not measure real model performance."
        )
    a, b, c = st.columns([2, 1, 1])
    with a:
        models = st.multiselect(
            "Models to compare",
            list(MODEL_LABELS),
            default=["lightgbm_global_v1", "rolling_mean"],
            format_func=MODEL_LABELS.get,
            max_selections=2,
        )
    with b:
        split = st.selectbox(
            "Historical split", ["test", "validation"], format_func=str.title
        )
    windows = [
        w
        for w in dataset["forecast_windows"]
        if w["model"] in models and w["split"] == split
    ]
    with c:
        maximum = min((w["max_horizon"] for w in windows), default=1)
        horizon = st.selectbox(
            "Forecast horizon",
            [None, *range(1, maximum + 1)],
            format_func=lambda n: "All horizons" if n is None else f"Day {n}",
        )
    st.caption(
        "Store and department filters apply here. Sales date filters apply to Overview; forecasts use the selected historical split."
    )
    if not models:
        st.info("Choose a model to view historical performance.")
        return
    params = [(k, v) for k, v in scope.items() if k in ("store", "department")]
    params += [("models", m) for m in models] + [("split", split)]
    if horizon:
        params += [("horizon", horizon)]
    result = client.request("/forecast", params=params)
    rows = result["result"]["rows"]
    for column, row in zip(st.columns(len(models)), rows, strict=False):
        with column:
            st.markdown(f"#### {MODEL_LABELS[row['model']]}")
            x, y, z = st.columns(3)
            x.metric(
                "WMAPE",
                "Undefined" if row["WMAPE"] is None else f"{row['WMAPE'] * 100:.2f}%",
                border=True,
            )
            y.metric("MAE", formatted(row["MAE"], 3), border=True)
            z.metric("RMSE", formatted(row["RMSE"], 3), border=True)
    if not rows:
        st.info("No predictions match the selected scope.")
        return
    daily = client.request("/forecast", params=params + [("segmentation", "day")])[
        "result"
    ]["rows"]
    observations = []
    first = rows[0]["model"]
    for row in daily:
        observations.append(
            {
                "Date": row["period"]["start"],
                "Units": row["predicted_units"],
                "Series": MODEL_LABELS[row["model"]],
            }
        )
        if row["model"] == first:
            observations.append(
                {
                    "Date": row["period"]["start"],
                    "Units": row["actual_units"],
                    "Series": "Observed actuals",
                }
            )
    st.markdown("#### Observed vs predicted demand")
    if observations:
        chart = (
            alt.Chart(pd.DataFrame(observations))
            .mark_line(strokeWidth=2.5, point=True)
            .encode(
                x=alt.X("Date:T", title=None),
                y=alt.Y("Units:Q", title="Daily units"),
                color=alt.Color(
                    "Series:N",
                    scale=alt.Scale(range=["#168494", "#253F66", "#D49A37"]),
                    legend=alt.Legend(orient="bottom"),
                ),
                tooltip=["Date:T", "Series", alt.Tooltip("Units:Q", format=",.2f")],
            )
        )
        st.altair_chart(chart, width="stretch", height=300)
    st.caption(
        "WMAPE is a ratio of summed errors to summed actual units. Model predictions are compared separately, never added. Accuracy describes historical backtests."
    )
    with st.expander("Forecast scope & provenance"):
        st.json(
            {
                "filters": result["result"]["filters"],
                "provenance": result["result"]["provenance"],
                "warnings": result["result"]["warnings"],
            }
        )


def answer_card(response):
    answer = response["result"]
    if response["live_provider_succeeded"]:
        st.success(
            f"Live local model · {answer['provider']} · {response['latency_ms'] / 1000:.2f}s"
        )
    elif answer["provider"].startswith("deterministic_fallback"):
        st.warning(
            f"Deterministic fallback · {answer['provider_diagnostic'].get('category', 'provider unavailable')}. This was not a live LLM answer."
        )
    else:
        st.caption(
            f"{answer['provider']} · {answer['status']} · {response['latency_ms'] / 1000:.2f}s"
        )
    st.markdown(answer["answer"])
    with st.expander("Sources, scope & provider diagnostics"):
        st.json(
            {
                "dataset": response["dataset"],
                "selected_tool": answer["tool"],
                "grounding_validated": answer["grounding_validated"],
                "provider_diagnostic": answer["provider_diagnostic"],
                "latency_ms": response["latency_ms"],
            }
        )


def assistant(client, health):
    dataset = health["dataset"]
    st.subheader("Ask RetailPulse")
    st.caption("One clear question. Approved tools. Verifiable answers.")
    options = ["ollama", "deterministic"]
    provider = st.radio(
        "Answer provider",
        options,
        index=1 if health["provider"]["default_mode"] == "deterministic" else 0,
        format_func=lambda p: (
            "Ollama · local model" if p == "ollama" else "Deterministic · offline"
        ),
        horizontal=True,
    )
    if provider == "ollama" and not health["provider"]["available"]:
        st.warning(
            "Ollama is unavailable. Start the local service or choose deterministic mode. Any fallback is explicitly disclosed."
        )
    lineage = dataset["lineage"]
    examples = [
        "How many units did CA_1 sell during April 2016?"
        if dataset["mode"] == "real"
        else f"Show units for {dataset['stores'][0]} from {lineage['observed_period']['start']} to {lineage['observed_period']['end']}",
        "Compare LightGBM and rolling mean WMAPE on the test period",
        "What does revenue_proxy mean?",
    ]
    pending = None
    for column, title, question in zip(
        st.columns(3),
        ("Explore store demand", "Compare forecast models", "Explain revenue proxy"),
        examples,
        strict=True,
    ):
        if column.button(title, width="stretch"):
            pending = question
    st.caption(
        "Each question is independent. Displayed chat history is not passed to the assistant; conversational follow-ups are not supported."
    )
    history = st.session_state.setdefault("rp_chat", [])
    for exchange in history:
        with st.chat_message("user"):
            st.write(exchange["question"])
        with st.chat_message("assistant"):
            answer_card(exchange["response"])
    pending = (
        st.chat_input(
            "Ask about historical units, metrics or forecast accuracy", max_chars=1000
        )
        or pending
    )
    if pending:
        with st.chat_message("user"):
            st.write(pending)
        with st.chat_message("assistant"):
            with st.spinner(
                "Checking scope and consulting approved tools. A cold local model may take up to 30 seconds."
            ):
                response = client.request(
                    "/assistant/query", body={"question": pending, "provider": provider}
                )
            answer_card(response)
        history.append({"question": pending, "response": response})
        del history[:-8]


def architecture(dataset):
    st.subheader("Trace every answer back to its source")
    st.caption(
        "A local analytical product, from raw observations to a grounded business answer."
    )
    for column, title, description in zip(
        st.columns(4),
        ("01 · Bronze", "02 · Silver", "03 · Gold / DuckDB", "04 · Decisions"),
        (
            "M5 CSV inputs, content hashes and immutable ingestion provenance.",
            "Validated daily sales, calendar and prices; explicit missing data.",
            "Canonical KPIs and read-only analytical tools. Every response carries source lineage.",
            "Forecasting / MLflow → Power BI, FastAPI, Streamlit and the grounded assistant.",
        ),
        strict=True,
    ):
        with column.container(border=True):
            st.markdown(f"**{title}**")
            st.write(description)
    st.markdown(
        "**M5 → Bronze → Silver → Gold/DuckDB → Forecasting/MLflow → Power BI / FastAPI / Streamlit / Grounded AI Assistant**"
    )
    left, right = st.columns(2)
    with left:
        st.markdown("#### Built to be checked")
        st.write(
            "Synthetic regression fixtures run without Kaggle or Ollama. Real-data acceptance separately reconciles API results with Gold. Frozen model artifacts and source hashes are preserved."
        )
        st.link_button(
            "Explore the metric catalog",
            "https://github.com/sjimenezch001/retailpulse-ai/blob/main/docs/metric_catalog.md",
        )
        st.link_button("Open the API documentation", API + "/docs")
    with right:
        st.markdown("#### Know the limits")
        st.write(
            "Historical observations are not current sales. M5 has no inventory data. Revenue is a proxy; spikes are heuristic. No AWS deployment or operational inventory analytics is claimed."
        )
        st.link_button(
            "Read the model card",
            "https://github.com/sjimenezch001/retailpulse-ai/blob/main/docs/model_card.md",
        )
        guide = ROOT / "docs/web_demo.md"
        if guide.is_file():
            st.download_button(
                "Download the demo guide",
                guide.read_text(encoding="utf-8"),
                file_name="RetailPulse-demo-guide.md",
                mime="text/markdown",
            )
    with st.expander("Dataset lineage"):
        st.json(dataset)


def main():
    st.set_page_config(
        page_title="RetailPulse AI · Retail demand intelligence",
        page_icon="◈",
        layout="wide",
    )
    st.markdown(
        """<style>
    .block-container{padding-top:2rem;max-width:1480px}h1,h2,h3{letter-spacing:-.035em}
    [data-testid="stMetricValue"]{font-size:1.55rem;font-weight:650}
    [data-testid="stMetricLabel"]{font-size:.8rem;color:#53647b}
    [data-baseweb="tab-list"]{gap:1.25rem;margin:1.2rem 0;border-bottom:1px solid #dce4ee}
    [data-baseweb="tab"]{font-size:1rem;padding:0.8rem 0.3rem}
    .eyebrow{color:#168494;letter-spacing:.15em;font-size:.75rem;font-weight:750}
    .intro{color:#60718b;font-size:1.06rem;margin-top:-.7rem}
    @media(max-width:900px){[data-testid="stMetricValue"]{font-size:1.15rem}.block-container{padding:1rem}}
    </style><div class="eyebrow">RETAILPULSE AI / DEMAND INTELLIGENCE</div>""",
        unsafe_allow_html=True,
    )
    st.title("See demand. Understand the evidence.")
    st.markdown(
        '<p class="intro">Retail analytics, honest forecasts and answers you can trace.</p>',
        unsafe_allow_html=True,
    )
    client = ApiClient(API)
    try:
        health = client.request("/health")
    except ApiClientError as exc:
        st.error(str(exc))
        st.code("python -m retailpulse demo", language="powershell")
        return
    dataset = health["dataset"]
    if not dataset:
        st.warning(health["message"])
        st.code(
            "python -m retailpulse demo --mode synthetic --provider deterministic",
            language="powershell",
        )
        return
    if st.session_state.get("rp_version") != dataset["dataset_version"]:
        for key in ("rp_chat", "sales_dates", "store", "department"):
            st.session_state.pop(key, None)
        st.session_state["rp_version"] = dataset["dataset_version"]
    if dataset["mode"] == "synthetic":
        st.warning(
            "SYNTHETIC PORTFOLIO DEMO · All observations and comparison series are illustrative. No real M5 data or trained-model performance."
        )
    else:
        st.caption("REAL M5 · HISTORICAL PILOT · Local and read-only")
    provenance(dataset)
    period = dataset["lineage"]["observed_period"]
    first, last = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
    with st.sidebar:
        st.markdown("### Your analysis scope")
        st.caption(dataset["label"])
        dates = st.date_input(
            "Sales date range",
            value=(first, last),
            min_value=first,
            max_value=last,
            key="sales_dates",
        )
        store = st.selectbox(
            "Store",
            [None, *dataset["stores"]],
            format_func=lambda s: s or "All stores",
            key="store",
        )
        department = st.selectbox(
            "Department",
            [None, *dataset["departments"]],
            format_func=lambda s: s or "All departments",
            key="department",
        )
        st.divider()
        st.markdown("**Snapshot freshness**")
        st.write(f"{dataset['lineage']['data_freshness']:,} days")
        st.caption(
            f"Measured at {dataset['lineage']['as_of_date']}; not pipeline latency."
        )
        st.caption("No current sales or inventory claims.")
    if len(dates) != 2:
        st.info("Choose both dates to complete the analysis range.")
        return
    scope = {"start_date": str(dates[0]), "end_date": str(dates[1])}
    if store:
        scope["store"] = store
    if department:
        scope["department"] = department
    tabs = st.tabs(["Overview", "Forecast", "Ask RetailPulse", "Architecture"])
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
            except ApiClientError as exc:
                st.error(str(exc))
    st.caption(
        "RetailPulse AI · Historical evidence, reproducible results · Portfolio demo"
    )


if __name__ == "__main__":
    main()
