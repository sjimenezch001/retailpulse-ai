CREATE TABLE mart_store_weekly AS
SELECT store_id, dept_id, wm_yr_wk,
    min(date) AS first_observed_date, max(date) AS last_observed_date,
    count(DISTINCT date) AS observed_days,
    sum(units) AS units,
    CASE WHEN count(sell_price) = count(*) THEN sum(revenue_proxy) END AS revenue_proxy,
    sum(revenue_proxy) AS known_revenue_proxy,
    count(*) FILTER (WHERE price_missing) AS missing_price_rows,
    count(sell_price) * 1.0 / count(*) AS price_coverage,
    max(data_freshness) AS data_freshness
FROM mart_sales_daily
GROUP BY store_id, dept_id, wm_yr_wk;
