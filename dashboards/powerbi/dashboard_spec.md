# RetailPulse dashboard specification

Exactly three native pages share a 1920 × 1080 canvas, 32 px outer margins,
24 px gutters, Segoe UI typography, neutral surfaces and a restrained teal,
slate and amber palette. The 49 containers comprise native cards, line/bar
charts, tables, slicers, text and page navigators. No custom chart runtime or
image-based dashboard is used. Critical numbers have explicit DAX measures.

## Analytical model

| Fact | Grain | Dimension paths | Rows in the validated pilot |
| --- | --- | --- | ---: |
| SalesDaily | Date × store × department | Date, Store, Department | 11,646 |
| SalesProductWeekly | Observed week × store × product | Week, Store, Product → Department | 512,076 |
| Forecast | Origin × target date × store × product × model × split | Date, Store, Product → Department, Model, Split, Horizon, Demand | 412,608 |
| Snapshot | Gold snapshot | Disconnected | 1 |

Relationships are many-to-one with single-direction dimension-to-fact filters.
Facts are never joined together. Date filters daily sales and forecast target
dates; Week filters diagnostics independently. Product has one Department
parent, preventing a second ambiguous Department route. Technical fact tables
and keys are hidden, implicit measures are discouraged, and the Date key is
unique. ComparisonModel is intentionally disconnected: comparison measures
replace only the selected model filter, retaining the other forecast filters.
Metrics is the measure home table. There are 15 tables and 14 relationships.

## Executive Overview

Default daily interval: 2016-03-28–2016-05-22; all stores and departments.
Five headline KPIs show Total Units, Known Revenue Proxy, Price Coverage,
Demand Spike Count and Data Freshness. Daily demand, rolling 7d/28d trends,
store/department bars, spike trends and an equal-length preceding-period
comparison explain movement. The previous interval is 2016-02-01–2016-03-27.

Known Revenue Proxy sums `units × sell_price` only where the price is known.
Canonical Revenue Proxy is BLANK whenever any selected observation lacks a
price; neither measure invents zero revenue for unknown prices. Price Coverage
uses observation counts, including zero-sales observations. The footer makes
the partial-revenue interpretation explicit. The default late-history period
has complete prices; full-history coverage is only 72.6631%.

Rolling values sum across series and average across dates when a visual spans
several dates. They are never summed across time. The global Data Freshness is
the gap between the last observed sales date and Gold's `as_of_date`, unaffected
by report refresh time or slicer selection. Missing/zero comparison periods
produce BLANK percentage changes. Gold's spike flag remains a heuristic.

## Store & Product Diagnostics

Week Start defaults to 2016-03-26–2016-05-21; all segments. Store, department
and product slicers select the weekly fact. Four KPIs summarize units, price
coverage, spikes and valid daily price changes. Store/department ranks, top and
bottom product charts, a weekly demand line and a context table expose segment
differences. Product ranking uses the first ten positive-demand **ranks**, so
ties can add rows. Zero-sales products are excluded; native scrollbars retain
all qualifying ranks. Bottom ranking therefore does not become a list of
unlaunched products.

Calendar event units and state-specific SNAP-period units are descriptive
subsets, not causal estimates. Average Price Change % is the mean of valid
Gold daily `price_change_pct` observations, converted from percentage points
to a DAX percentage fraction. It is not a compounded return. Boundary weeks
may contain fewer observed days; the footer discloses that limitation.

## Forecast Performance

Default model: LightGBM; split: test; all stores, departments, horizons and
demand levels. The date interval contains both 28-day backtests so changing
split does not require clearing the date selection. Seven slicers cover target
date, model, split, store, department, horizon and origin-derived demand level.

WMAPE, MAE, RMSE and signed bias cards accompany actual/predicted demand,
all-model comparison, horizon comparison against rolling mean, store/department
WMAPE and a demand-level table. WMAPE is `sum(abs(error))/sum(abs(actual))`,
not an average of segment ratios. MAE uses summed error divided by count; RMSE
uses the square root of mean squared error. Zero actual denominators remain
BLANK. Actual Units deduplicates across models; Predicted Units and forecast
variance require one model. Future forecasts with unknown actuals are excluded.

The frozen LightGBM model improves full-test WMAPE and MAE over rolling mean
but worsens RMSE. The footer retains that tradeoff. Segment filters can change
the ranking; no BI step retunes or retrains the model. The four-model table
remains a comparison even when the model selector chooses one model.

## Interaction and presentation contract

Navigation uses the native page navigator. Slicers are page-local; switching
pages preserves each page's context. Chart selection uses Power BI's native
cross-filter/highlight behavior. No bidirectional model relationship is needed.
Users can inspect filtered values through native tooltips and table rows.

Report titles, descriptions, measures and authored labels are English.
Power BI's date-axis abbreviations and numeric separators follow the local
Desktop regional settings; the captured Windows environment uses Spanish
regional formatting. This does not change data types, formulas or the English
source definitions. M parses source CSVs with explicit `en-US` typing.

The [measure contract](measures.md) contains all 34 formulas, Gold sources,
filter behavior, null rules and SQL equivalents. The [build guide](BUILD_GUIDE.md)
documents refresh and portability. The [gate](../../docs/evidence/rp08_gate.md)
links genuine rendering and aggregate validation evidence.
