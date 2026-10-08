# Power BI measure contract

All SQL examples apply the same filter predicates and grains as their DAX context. `bi_*` views are defined by `sql/bi/serving.sql`. Revenue is a proxy, not audited financial revenue. Weekly diagnostics select whole observed weeks. Forecast metrics use backtests only.

## Total Units

```dax
SUM(SalesDaily[Units])
```

Observed units in the selected daily period.

Gold source: `mart_sales_daily.units`.

Filters: Date, store and department.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(units) FROM bi_sales_daily;
```

## Sales Observations

```dax
SUM(SalesDaily[Observations])
```

Underlying item/store/day count.

Gold source: `mart_sales_daily`.

Filters: Date, store and department.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(observation_count) FROM bi_sales_daily;
```

## Priced Observations

```dax
SUM(SalesDaily[Priced Observations])
```

Observations with a known price, including zero sales.

Gold source: `mart_sales_daily.sell_price`.

Filters: Date, store and department.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(priced_count) FROM bi_sales_daily;
```

## Known Revenue Proxy

```dax
SUM(SalesDaily[Known Revenue])
```

Partial units-times-price sum for known prices; not audited revenue.

Gold source: `mart_sales_daily.revenue_proxy`.

Filters: Date, store and department.

Missing values: Unknown prices are excluded; all unknown is BLANK, never zero-filled.

SQL verification:

```sql
SELECT sum(revenue_proxy) FROM mart_sales_daily;
```

## Price Coverage

```dax
DIVIDE([Priced Observations], [Sales Observations])
```

Share of observations with known prices.

Gold source: `mart_sales_daily.sell_price`.

Filters: Date, store and department.

Missing values: BLANK for an empty denominator.

SQL verification:

```sql
SELECT count(sell_price)::DOUBLE/nullif(count(*),0) FROM mart_sales_daily;
```

## Canonical Revenue Proxy

```dax
IF([Sales Observations] = [Priced Observations], [Known Revenue Proxy])
```

Conservative canonical revenue: unknown if any price is missing.

Gold source: `mart_sales_daily.revenue_proxy`.

Filters: Date, store and department.

Missing values: BLANK whenever any included price is unknown.

SQL verification:

```sql
SELECT CASE WHEN count(sell_price)=count(*) THEN sum(revenue_proxy) END FROM mart_sales_daily;
```

## Revenue Proxy Completeness

```dax
IF(ISBLANK([Sales Observations]), "No observations", IF([Sales Observations] = [Priced Observations], "Complete price coverage", "Partial: missing prices"))
```

Readable completeness disclosure beside known-price partial revenue.

Gold source: `mart_sales_daily.sell_price`.

Filters: Date, store and department.

Missing values: Displays No observations for an empty selection.

SQL verification:

```sql
SELECT CASE WHEN count(*)=0 THEN 'No observations' WHEN count(sell_price)=count(*) THEN 'Complete price coverage' ELSE 'Partial: missing prices' END FROM mart_sales_daily;
```

## Rolling 7D Demand

```dax
AVERAGEX(VALUES('Date'[Date]), CALCULATE(SUM(SalesDaily[Rolling7])))
```

Sum across series, then average across selected dates; never add rolling values across dates.

Gold source: `mart_sales_daily.rolling_7d`.

Filters: Date, store and department.

Missing values: Incomplete-history dates remain BLANK and are excluded from the date average.

SQL verification:

```sql
SELECT avg(demand) FROM (SELECT date,sum(rolling_7d) demand FROM mart_sales_daily GROUP BY date);
```

## Rolling 28D Demand

```dax
AVERAGEX(VALUES('Date'[Date]), CALCULATE(SUM(SalesDaily[Rolling28])))
```

Sum across series, then average across selected dates; never add rolling values across dates.

Gold source: `mart_sales_daily.rolling_28d`.

Filters: Date, store and department.

Missing values: Incomplete-history dates remain BLANK and are excluded from the date average.

SQL verification:

```sql
SELECT avg(demand) FROM (SELECT date,sum(rolling_28d) demand FROM mart_sales_daily GROUP BY date);
```

## Previous Period Units

```dax
VAR StartDate = MIN('Date'[Date]) VAR Days = INT(MAX('Date'[Date]) - StartDate) + 1 RETURN CALCULATE([Total Units], REMOVEFILTERS('Date'), DATESBETWEEN('Date'[Date], StartDate - Days, StartDate - 1))
```

Units in the immediately preceding equal-length daily interval.

Gold source: `mart_sales_daily.units`.

Filters: Replaces the date filter; preserves store and department. Use a contiguous date range.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(units) FROM mart_sales_daily WHERE date BETWEEN $start - ($end-$start+1) AND $start - 1;
```

## Period-over-Period Change

```dax
IF(NOT ISBLANK([Previous Period Units]) && NOT ISBLANK([Total Units]), [Total Units] - [Previous Period Units])
```

Absolute unit change versus the preceding equal-length interval.

Gold source: `mart_sales_daily.units`.

Filters: Date, store and department.

Missing values: BLANK when no observations match.

SQL verification:

```sql
WITH periods AS (SELECT sum(units) FILTER(WHERE date BETWEEN $start AND $end) current_units, sum(units) FILTER(WHERE date BETWEEN $start - ($end-$start+1) AND $start - 1) previous_units FROM mart_sales_daily) SELECT current_units - previous_units FROM periods;
```

## Period-over-Period Change %

```dax
DIVIDE([Period-over-Period Change], [Previous Period Units])
```

Relative unit change versus the preceding period.

Gold source: `mart_sales_daily.units`.

Filters: Date, store and department.

Missing values: BLANK for missing or zero previous-period units.

SQL verification:

```sql
WITH periods AS (SELECT sum(units) FILTER(WHERE date BETWEEN $start AND $end) current_units, sum(units) FILTER(WHERE date BETWEEN $start - ($end-$start+1) AND $start - 1) previous_units FROM mart_sales_daily) SELECT (current_units-previous_units)/nullif(previous_units,0) FROM periods;
```

## Demand Spike Count

```dax
SUM(SalesDaily[Spikes])
```

Item/store/day flags from the canonical heuristic, not confirmed causal events.

Gold source: `mart_sales_daily.demand_spike_flag`.

Filters: Date, store and department.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT count(*) FROM mart_demand_alerts;
```

## Data Freshness

```dax
MAX(Snapshot[Freshness Days])
```

Days from last observed sales to the Gold as_of date; independent of refresh time.

Gold source: `pipeline_metadata`.

Filters: Global snapshot, unaffected by segment or date filters.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT date_diff('day',last_sales_date,as_of_date) FROM pipeline_metadata;
```

## Product Units

```dax
SUM(SalesProductWeekly[Units])
```

Observed units over selected whole weeks.

Gold source: `mart_sales_daily joined to dim_calendar`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(units) FROM bi_sales_product_week;
```

## Product Spike Count

```dax
SUM(SalesProductWeekly[Spikes])
```

Canonical spike flags in selected product-weeks.

Gold source: `mart_sales_daily joined to dim_calendar`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(spike_count) FROM bi_sales_product_week;
```

## Event-period Units

```dax
SUM(SalesProductWeekly[Event Units])
```

Units observed on event days; descriptive association only.

Gold source: `mart_sales_daily joined to dim_calendar`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(event_units) FROM bi_sales_product_week;
```

## SNAP-period Units

```dax
SUM(SalesProductWeekly[SNAP Units])
```

Units observed on state SNAP days; descriptive association only.

Gold source: `mart_sales_daily joined to dim_calendar`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(snap_units) FROM bi_sales_product_week;
```

## Product Price Coverage

```dax
DIVIDE(SUM(SalesProductWeekly[Priced Observations]),SUM(SalesProductWeekly[Observations]))
```

Price coverage for selected products and observed weeks.

Gold source: `mart_sales_daily.sell_price`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(priced_count)::DOUBLE/nullif(sum(observation_count),0) FROM bi_sales_product_week;
```

## Average Price Change %

```dax
DIVIDE(SUM(SalesProductWeekly[Price Change Sum]),SUM(SalesProductWeekly[Price Change Count])) / 100
```

Mean of valid daily Gold price changes; noncausal, not a period price return.

Gold source: `mart_sales_daily.price_change_pct`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: Undefined daily changes are excluded; BLANK when none are valid.

SQL verification:

```sql
SELECT sum(price_change_sum)/nullif(sum(price_change_count),0)/100 FROM bi_sales_product_week;
```

## Top Product Units

```dax
VAR Demand = [Product Units] VAR Position = RANKX(FILTER(ALLSELECTED(Product[Product]), CALCULATE([Product Units]) > 0), [Product Units], , DESC, DENSE) RETURN IF(Demand > 0 && Position <= 10, Demand)
```

First ten positive-demand ranks; includes ties, zero-demand products are excluded.

Gold source: `mart_sales_daily.units`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: Nonpositive demand and ranks beyond ten return BLANK.

SQL verification:

```sql
SELECT item_id,sum(units) AS units FROM bi_sales_product_week GROUP BY item_id HAVING sum(units)>0 QUALIFY dense_rank() OVER(ORDER BY sum(units) DESC)<=10 ORDER BY units DESC,item_id;
```

## Bottom Product Units

```dax
VAR Demand = [Product Units] VAR Position = RANKX(FILTER(ALLSELECTED(Product[Product]), CALCULATE([Product Units]) > 0), [Product Units], , ASC, DENSE) RETURN IF(Demand > 0 && Position <= 10, Demand)
```

First ten positive-demand ranks; includes ties, zero-demand products are excluded.

Gold source: `mart_sales_daily.units`.

Filters: Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact.

Missing values: Nonpositive demand and ranks beyond ten return BLANK.

SQL verification:

```sql
SELECT item_id,sum(units) AS units FROM bi_sales_product_week GROUP BY item_id HAVING sum(units)>0 QUALIFY dense_rank() OVER(ORDER BY sum(units) ASC)<=10 ORDER BY units ASC,item_id;
```

## Forecast Observations

```dax
COUNTROWS(Forecast)
```

Number of scored model/series/day predictions.

Gold source: `fact_forecast`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT count(*) FROM bi_forecast;
```

## Actual Units

```dax
SUMX(SUMMARIZE(Forecast, Forecast[Forecast Origin], Forecast[Target Date], Forecast[Store], Forecast[Product], Forecast[Split], "Observed", MAX(Forecast[Actual Units])), [Observed])
```

Observed units counted once per series/date/split even if several models are selected.

Gold source: `fact_forecast.actual_units`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sum(actual) FROM (SELECT forecast_origin,target_date,store_id,item_id,split,max(actual_units) actual FROM bi_forecast GROUP BY ALL);
```

## Predicted Units

```dax
IF(HASONEVALUE('Model'[ModelKey]),SUM(Forecast[Predicted Units]))
```

Forecast units for the single selected model.

Gold source: `fact_forecast.predicted_units`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK unless exactly one model is selected; forecasts from different models are never added together.

SQL verification:

```sql
SELECT sum(predicted_units) FROM bi_forecast WHERE model=$model;
```

## WMAPE

```dax
DIVIDE(SUM(Forecast[Absolute Error]),SUM(Forecast[Actual Units]))
```

Canonical ratio of summed absolute error to actual units; never an average of segment WMAPEs.

Gold source: `fact_forecast`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK for a zero actual-unit denominator.

SQL verification:

```sql
SELECT sum(absolute_error)/nullif(sum(abs(actual_units)),0) FROM bi_forecast;
```

## MAE

```dax
DIVIDE(SUM(Forecast[Absolute Error]),[Forecast Observations])
```

Mean absolute error in units.

Gold source: `fact_forecast`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT avg(absolute_error) FROM bi_forecast;
```

## RMSE

```dax
VAR MSE = DIVIDE(SUM(Forecast[Squared Error]),[Forecast Observations]) RETURN IF(NOT ISBLANK(MSE), SQRT(MSE))
```

Root mean squared error in units.

Gold source: `fact_forecast`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT sqrt(avg(squared_error)) FROM bi_forecast;
```

## Forecast Bias

```dax
DIVIDE(SUM(Forecast[Signed Error]),SUM(Forecast[Actual Units]))
```

Signed relative bias; positive is overprediction.

Gold source: `fact_forecast`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK for zero actual units.

SQL verification:

```sql
SELECT sum(predicted_units-actual_units)/nullif(sum(actual_units),0) FROM bi_forecast;
```

## Forecast versus Actual Variance

```dax
IF(HASONEVALUE('Model'[ModelKey]),[Predicted Units] - [Actual Units])
```

Absolute forecast-minus-actual unit difference for the selected model.

Gold source: `fact_forecast`.

Filters: Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins.

Missing values: BLANK for multiple or no models.

SQL verification:

```sql
SELECT sum(predicted_units)-sum(actual_units) FROM bi_forecast WHERE model=$model;
```

## Comparison WMAPE

```dax
CALCULATE([WMAPE], REMOVEFILTERS('Model'), TREATAS(VALUES(ComparisonModel[ModelKey]),'Model'[ModelKey]))
```

All-model benchmark, retaining the other selected filters.

Gold source: `fact_forecast`.

Filters: Comparison model replaces the model selector; all other forecast filters remain active.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT model, sum(absolute_error)/nullif(sum(abs(actual_units)),0) FROM bi_forecast GROUP BY model;
```

## Comparison MAE

```dax
CALCULATE([MAE], REMOVEFILTERS('Model'), TREATAS(VALUES(ComparisonModel[ModelKey]),'Model'[ModelKey]))
```

All-model benchmark, retaining the other selected filters.

Gold source: `fact_forecast`.

Filters: Comparison model replaces the model selector; all other forecast filters remain active.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT model, avg(absolute_error) FROM bi_forecast GROUP BY model;
```

## Comparison RMSE

```dax
CALCULATE([RMSE], REMOVEFILTERS('Model'), TREATAS(VALUES(ComparisonModel[ModelKey]),'Model'[ModelKey]))
```

All-model benchmark, retaining the other selected filters.

Gold source: `fact_forecast`.

Filters: Comparison model replaces the model selector; all other forecast filters remain active.

Missing values: BLANK when no observations match.

SQL verification:

```sql
SELECT model, sqrt(avg(squared_error)) FROM bi_forecast GROUP BY model;
```

## Rolling Mean WMAPE

```dax
CALCULATE([WMAPE], REMOVEFILTERS('Model'), 'Model'[ModelKey] = "rolling_mean")
```

Rolling-mean benchmark on the same selected backtest observations.

Gold source: `fact_forecast`.

Filters: Replaces only the model filter; all other forecast filters remain active.

Missing values: BLANK for no observations or zero actual units.

SQL verification:

```sql
SELECT sum(absolute_error)/nullif(sum(abs(actual_units)),0) FROM bi_forecast WHERE model='rolling_mean';
```
