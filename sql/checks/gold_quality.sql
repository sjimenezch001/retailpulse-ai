-- A nonempty result is a quality failure.
SELECT 'duplicate_daily_key' AS failure
WHERE EXISTS (
    SELECT 1 FROM mart_sales_daily GROUP BY date, store_id, item_id HAVING count(*) > 1
)
UNION ALL SELECT 'negative_or_null_units'
WHERE EXISTS (SELECT 1 FROM mart_sales_daily WHERE units IS NULL OR units < 0)
UNION ALL SELECT 'silver_gold_units_mismatch'
WHERE (SELECT sum(units) FROM fact_sales_daily) IS DISTINCT FROM
      (SELECT sum(units) FROM mart_sales_daily)
UNION ALL SELECT 'daily_weekly_units_mismatch'
WHERE (SELECT sum(units) FROM mart_sales_daily) IS DISTINCT FROM
      (SELECT sum(units) FROM mart_store_weekly)
UNION ALL SELECT 'missing_price_dropped'
WHERE (SELECT count(*) FROM fact_sales_daily WHERE price_missing) !=
      (SELECT count(*) FROM mart_sales_daily WHERE price_missing)
UNION ALL SELECT 'row_count_mismatch'
WHERE (SELECT count(*) FROM fact_sales_daily) != (SELECT count(*) FROM mart_sales_daily)
UNION ALL SELECT 'invalid_revenue_proxy'
WHERE EXISTS (
    SELECT 1 FROM mart_sales_daily
    WHERE (price_missing AND revenue_proxy IS NOT NULL)
       OR (NOT price_missing AND abs(revenue_proxy - units * sell_price) > 0.00000001)
);
