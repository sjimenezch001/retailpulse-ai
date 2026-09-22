# RetailPulse AI — Product Brief

## Product
RetailPulse AI is a retail demand analytics platform that transforms historical sales, calendar/events and prices into verifiable metrics, comparisons by store/department and demand forecasts.

## Target user

- Commercial management: understand where demand changes and which segments explain the variation.
- BI analyst: query KPIs with consistent definitions and controlled filters.
- Planning: review forecasts and historical error by segment.
- Data team: trace which batch, transformation and model produced each figure.

## Problem
Retail teams can end up with fragmented analysis and inconsistent metric definitions. RetailPulse AI centralizes the flow from raw data to KPIs, forecasting and assisted queries, preserving traceability and reproducibility.

## MVP pilot
M5 Forecasting — Accuracy dataset.

Configurable initial subset:

- 3 stores
- 2 departments

The specific selection will be defined in configuration during RP-02; it will not be hardcoded.

## Decisions supported

1. How units and revenue_proxy have evolved over recent weeks.
2. Which stores or departments explain the largest variation.
3. What demand is expected over the selected horizon and what the historical error is.
4. Which events or price changes coincide with changes in demand.
5. How each metric is defined and which table/period it comes from.

## Locked MVP scope

- Reproducible batch ingestion.
- Bronze / Silver / Gold layers.
- Contracts and quality tests.
- KPIs and SQL semantic layer.
- Forecasting baseline and candidate model.
- Three-page Power BI dashboard.
- FastAPI API.
- AI assistant with read-only tools and verifiable figures.
- Local reproducibility and technical README.

## Limitations and product transparency

- M5 does not contain actual inventory data.
- revenue_proxy = units × sell_price; it does not represent audited accounting revenue.
- Demand alerts do not imply causality.
- Any replenishment scenario will be simulated and labeled as such.
- The MVP must run locally without mandatory costs.

## Demonstrable outcome
In under 3 minutes, a user should be able to view the data flow, query KPIs, compare stores/departments, review a forecast and get an assistant response with its source, period and update date.

## RP-00 success criteria

- The problem can be explained in ~30 seconds.
- Each Must feature answers a business question.
- An explicit list of exclusions exists.
- No new features are added to the MVP without first being added to the backlog.
