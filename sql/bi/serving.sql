-- Local, read-only Gold projections. Daily and observed-week grains are explicit.
CREATE TEMP VIEW bi_date AS
SELECT c.date::DATE AS date, c.year, c.month,
       strftime(c.date, '%Y-%m') AS year_month, c.weekday,
       coalesce(nullif(c.event_name_1, ''), nullif(c.event_name_2, ''), 'No event') AS event_context
FROM dim_calendar c, pipeline_metadata p
WHERE c.date BETWEEN p.first_sales_date AND p.last_sales_date;

CREATE TEMP VIEW bi_week AS
SELECT wm_yr_wk AS week_key, min(date)::DATE AS week_start,
       max(date)::DATE AS week_end, count(DISTINCT date) AS observed_days
FROM mart_sales_daily GROUP BY wm_yr_wk;

CREATE TEMP VIEW bi_store AS SELECT store_id, state_id FROM dim_store;
CREATE TEMP VIEW bi_department AS SELECT DISTINCT dept_id FROM dim_product;
CREATE TEMP VIEW bi_product AS SELECT item_id, dept_id, cat_id FROM dim_product;
CREATE TEMP VIEW bi_model AS
SELECT DISTINCT model,
       CASE model WHEN 'lightgbm_global_v1' THEN 'LightGBM'
                  WHEN 'rolling_mean' THEN 'Rolling mean'
                  WHEN 'last_value' THEN 'Last value'
                  WHEN 'seasonal_naive_7' THEN 'Seasonal naive (7D)' ELSE model END AS model_name
FROM fact_forecast WHERE actual_units IS NOT NULL;
CREATE TEMP VIEW bi_split AS SELECT DISTINCT split FROM fact_forecast WHERE actual_units IS NOT NULL;
CREATE TEMP VIEW bi_demand_level AS SELECT DISTINCT demand_level FROM fact_forecast WHERE actual_units IS NOT NULL;
CREATE TEMP VIEW bi_horizon AS SELECT DISTINCT horizon FROM fact_forecast WHERE actual_units IS NOT NULL;

CREATE TEMP VIEW bi_sales_daily AS
SELECT date::DATE AS date, store_id, dept_id, sum(units)::BIGINT AS units,
       sum(revenue_proxy) AS known_revenue_proxy,
       count(*) AS observation_count, count(sell_price) AS priced_count,
       sum(rolling_7d) AS rolling_7d_units, sum(rolling_28d) AS rolling_28d_units,
       count(*) FILTER (WHERE demand_spike_flag) AS spike_count
FROM mart_sales_daily GROUP BY date, store_id, dept_id;

CREATE TEMP VIEW bi_sales_product_week AS
SELECT s.wm_yr_wk AS week_key, s.store_id, s.item_id,
       sum(s.units)::BIGINT AS units, sum(s.revenue_proxy) AS known_revenue_proxy,
       count(*) AS observation_count, count(s.sell_price) AS priced_count,
       count(*) FILTER (WHERE s.demand_spike_flag) AS spike_count,
       sum(s.price_change_pct) AS price_change_sum,
       count(s.price_change_pct) AS price_change_count,
       sum(CASE WHEN nullif(c.event_name_1,'') IS NOT NULL
                       OR nullif(c.event_name_2,'') IS NOT NULL THEN s.units ELSE 0 END)::BIGINT AS event_units,
       sum(CASE WHEN CASE s.state_id WHEN 'CA' THEN c.snap_CA WHEN 'TX' THEN c.snap_TX
                                    WHEN 'WI' THEN c.snap_WI ELSE 0 END = 1
                THEN s.units ELSE 0 END)::BIGINT AS snap_units
FROM mart_sales_daily s JOIN dim_calendar c USING (date)
GROUP BY s.wm_yr_wk, s.store_id, s.item_id;

CREATE TEMP VIEW bi_forecast AS
SELECT forecast_origin, target_date, store_id, item_id, model, split, horizon, demand_level,
       predicted_units, actual_units, abs(actual_units - predicted_units) AS absolute_error,
       pow(actual_units - predicted_units, 2) AS squared_error,
       predicted_units - actual_units AS signed_error, source_run_id
FROM fact_forecast WHERE actual_units IS NOT NULL;

CREATE TEMP VIEW bi_metadata AS
SELECT p.gold_run_id, p.silver_run_id, p.bronze_run_id, p.first_sales_date, p.last_sales_date,
       p.as_of_date, date_diff('day', p.last_sales_date, p.as_of_date) AS data_freshness,
       (SELECT count(*) FROM fact_forecast WHERE actual_units IS NULL) AS excluded_future_forecasts,
       (SELECT freeze_sha256 FROM model_run WHERE model='lightgbm_global_v1') AS model_freeze_sha256
FROM pipeline_metadata p;
