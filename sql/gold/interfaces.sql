CREATE TABLE fact_forecast (
    forecast_origin DATE NOT NULL,
    target_date DATE NOT NULL,
    store_id VARCHAR NOT NULL,
    item_id VARCHAR NOT NULL,
    dept_id VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    split VARCHAR NOT NULL,
    horizon INTEGER NOT NULL CHECK (horizon > 0),
    predicted_units DOUBLE NOT NULL CHECK (predicted_units >= 0 AND isfinite(predicted_units)),
    actual_units DOUBLE CHECK (actual_units >= 0 AND isfinite(actual_units)),
    demand_level VARCHAR NOT NULL,
    training_start DATE NOT NULL,
    training_end DATE NOT NULL,
    source_run_id VARCHAR NOT NULL,
    PRIMARY KEY (forecast_origin, target_date, store_id, item_id, model, split),
    CHECK (training_start <= training_end AND training_end = forecast_origin),
    CHECK (target_date > forecast_origin)
);

CREATE TABLE forecast_evaluation (
    split VARCHAR, model VARCHAR, segment_type VARCHAR, segment VARCHAR,
    observations BIGINT, WMAPE DOUBLE, MAE DOUBLE, RMSE DOUBLE,
    wmape_zero_denominator BOOLEAN, source_run_id VARCHAR
);

CREATE VIEW mart_demand_alerts AS
SELECT date, store_id, item_id, dept_id, units, rolling_28d,
       demand_spike_flag, price_change_pct, pipeline_run_id
FROM mart_sales_daily
WHERE demand_spike_flag;

CREATE TABLE metric_definitions AS
SELECT * FROM (VALUES
 ('units', 'date × store × item', 'Observed nonnegative daily unit sales', 'Date, store, department, item'),
 ('revenue_proxy', 'date × store × item', 'units * sell_price; NULL when price is missing; proxy, not audited revenue', 'Date, store, department, item; aggregate is NULL if any included price is missing'),
 ('rolling_7d', 'date × store × item', 'Mean units over the previous 7 days, excluding today; NULL until 7 days exist', 'Filter after window calculation; not additive across dates'),
 ('rolling_28d', 'date × store × item', 'Mean units over the previous 28 days, excluding today; NULL until 28 days exist', 'Filter after window calculation; not additive across dates'),
 ('price_change_pct', 'date × store × item', '100 * (price - previous day price) / previous day price; NULL for missing or zero denominator', 'Date, store, department, item; not additive'),
 ('demand_spike_flag', 'date × store × item', 'units > 2 * previous 28-day mean with complete history and positive mean; otherwise false; no causality claim', 'Date, store, department, item'),
 ('data_freshness', 'dataset snapshot', 'Calendar days from latest observed sales date to explicit as_of date', 'Global snapshot metric; not recomputed for a segment filter')
) AS definitions(metric, grain, definition, filters);
