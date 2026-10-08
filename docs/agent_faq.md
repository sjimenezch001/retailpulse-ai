# Grounded assistant FAQ

## Historical observations and freshness

RetailPulse uses historical M5 observations, not live store sales.
`data_freshness` measures calendar days between the latest observed sales date
and Gold's explicit `as_of_date`; a new dashboard or assistant request does
not make the underlying observations current. Ask for an explicit historical
period, or ask the assistant for data freshness and the observed date range.

## Inventory and stockouts

M5 provides no actual inventory observations. Zero sales do not prove a
stockout, lost demand or unavailable inventory. The assistant cannot infer
inventory quantities or prescribe replenishment orders from these data.

## Revenue and missing prices

`revenue_proxy` is units multiplied by selling price, not audited revenue.
Its canonical aggregate is unknown if any selected price is missing.
`known_revenue_proxy` is the separate partial sum of priced observations.
`price_coverage` is the share of observations with known prices, including
zero-sales observations. Missing prices are not replaced with known zeros.

## Rolling demand and spikes

`rolling_7d` and `rolling_28d` use only preceding observations, excluding the
current day. Aggregate rolling demand sums series per day, then averages
valid daily sums across the requested period. `demand_spike_flag` is a
heuristic review signal. Neither spikes nor price/calendar associations prove
causation.

## Forecast evaluation and future predictions

WMAPE is the ratio of summed absolute errors to summed absolute actual units;
it is not the average of subgroup percentages. MAE is mean absolute error,
and RMSE is root mean squared error. WMAPE is undefined for a zero denominator.
Historical validation/test results are backtests, not future guarantees.
Baseline future predictions extend beyond their historical forecast origin;
they are not predictions for today's stores. LightGBM currently supplies
historical validation/test predictions only. Future observations and future
accuracy metrics are unavailable.

## Supported questions and local privacy

Ask for one approved KPI with explicit date bounds, one named month/year, or
all observed dates. Filters accept one store, department and optional product.
Forecast comparisons accept approved model names and one evaluation split.
Unclear requests receive clarification. Unsupported operations receive an
explicit limitation. Each numerical answer exposes its filters, period and
Gold provenance. Runtime traces store outcomes and validated filters without
the original question or full result. Documents are reference data only.
