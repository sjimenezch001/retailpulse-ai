-- Q1: daily evolution. Aggregated proxy is unknown if any price is missing.
SELECT date, sum(units) AS units,
       CASE WHEN count(sell_price) = count(*) THEN sum(revenue_proxy) END AS revenue_proxy,
       count(*) FILTER (WHERE price_missing) AS missing_price_rows
FROM mart_sales_daily
GROUP BY date ORDER BY date;
