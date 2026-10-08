SELECT count(*) AS fact_rows,
       count(DISTINCT concat(cast(date AS varchar), '|', store_id, '|', item_id)) AS unique_keys,
       sum(CASE WHEN units IS NULL OR units < 0 THEN 1 ELSE 0 END) AS invalid_units,
       sum(CASE WHEN sell_price IS NULL THEN 1 ELSE 0 END) AS missing_price_rows,
       sum(CASE WHEN (sell_price IS NULL AND (NOT price_missing OR revenue_proxy IS NOT NULL))
                  OR (sell_price IS NOT NULL AND (price_missing OR revenue_proxy IS NULL))
                THEN 1 ELSE 0 END) AS invalid_null_semantics,
       min(date) AS first_date, max(date) AS last_date
FROM mart_sales_daily;
