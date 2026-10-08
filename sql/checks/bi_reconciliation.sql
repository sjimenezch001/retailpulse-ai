-- Return only failures. Each projection reconciles independently to Gold.
WITH forecast_metrics AS (
    SELECT model, split, count(*) AS observations,
           sum(absolute_error) / nullif(sum(abs(actual_units)), 0) AS WMAPE,
           avg(absolute_error) AS MAE, sqrt(avg(squared_error)) AS RMSE
    FROM bi_forecast GROUP BY model, split
)
SELECT 'daily_units' AS failure
WHERE (SELECT sum(units) FROM bi_sales_daily) != (SELECT sum(units) FROM mart_sales_daily)
UNION ALL SELECT 'product_week_units'
WHERE (SELECT sum(units) FROM bi_sales_product_week) != (SELECT sum(units) FROM mart_sales_daily)
UNION ALL SELECT 'observation_counts'
WHERE (SELECT sum(observation_count) FROM bi_sales_daily) != (SELECT count(*) FROM mart_sales_daily)
   OR (SELECT sum(observation_count) FROM bi_sales_product_week) != (SELECT count(*) FROM mart_sales_daily)
UNION ALL SELECT 'price_coverage'
WHERE (SELECT sum(priced_count) FROM bi_sales_daily) != (SELECT count(sell_price) FROM mart_sales_daily)
   OR (SELECT sum(priced_count) FROM bi_sales_product_week) != (SELECT count(sell_price) FROM mart_sales_daily)
UNION ALL SELECT 'known_revenue_proxy'
WHERE abs((SELECT sum(known_revenue_proxy) FROM bi_sales_daily) - (SELECT sum(revenue_proxy) FROM mart_sales_daily)) > 0.01
   OR abs((SELECT sum(known_revenue_proxy) FROM bi_sales_product_week) - (SELECT sum(revenue_proxy) FROM mart_sales_daily)) > 0.01
   OR ((SELECT sum(known_revenue_proxy) FROM bi_sales_daily) IS NULL) != ((SELECT sum(revenue_proxy) FROM mart_sales_daily) IS NULL)
   OR ((SELECT sum(known_revenue_proxy) FROM bi_sales_product_week) IS NULL) != ((SELECT sum(revenue_proxy) FROM mart_sales_daily) IS NULL)
UNION ALL SELECT 'spikes'
WHERE (SELECT sum(spike_count) FROM bi_sales_daily) != (SELECT count(*) FROM mart_demand_alerts)
UNION ALL SELECT 'date_bounds'
WHERE (SELECT min(date) FROM bi_date) != (SELECT first_sales_date FROM pipeline_metadata)
   OR (SELECT max(date) FROM bi_date) != (SELECT last_sales_date FROM pipeline_metadata)
UNION ALL SELECT 'dimensions'
WHERE (SELECT count(*) FROM bi_store) != (SELECT count(DISTINCT store_id) FROM mart_sales_daily)
   OR (SELECT count(*) FROM bi_department) != (SELECT count(DISTINCT dept_id) FROM mart_sales_daily)
UNION ALL SELECT 'forecast_rows'
WHERE (SELECT count(*) FROM bi_forecast) != (SELECT count(*) FROM fact_forecast WHERE actual_units IS NOT NULL)
UNION ALL SELECT 'forecast_uniqueness'
WHERE EXISTS (SELECT 1 FROM bi_forecast GROUP BY forecast_origin,target_date,store_id,item_id,model,split HAVING count(*) > 1)
UNION ALL SELECT 'forecast_horizon'
WHERE EXISTS (SELECT 1 FROM bi_forecast WHERE horizon != date_diff('day',forecast_origin,target_date) OR horizon < 1)
UNION ALL SELECT 'forecast_metrics'
WHERE EXISTS (
    SELECT 1 FROM forecast_metrics f FULL OUTER JOIN
        (SELECT * FROM forecast_evaluation WHERE segment_type='overall') e USING (model,split)
    WHERE f.observations IS DISTINCT FROM e.observations
       OR abs(f.WMAPE-e.WMAPE)>1e-10 OR abs(f.MAE-e.MAE)>1e-10 OR abs(f.RMSE-e.RMSE)>1e-10
       OR (f.WMAPE IS NULL) != (e.WMAPE IS NULL)
       OR (f.MAE IS NULL) != (e.MAE IS NULL) OR (f.RMSE IS NULL) != (e.RMSE IS NULL)
)
UNION ALL SELECT 'lineage'
WHERE EXISTS (SELECT 1 FROM bi_forecast WHERE source_run_id IS DISTINCT FROM (SELECT gold_run_id FROM pipeline_metadata))
   OR (SELECT count(*) FROM bi_metadata) != 1;
