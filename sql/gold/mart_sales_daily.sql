-- Canonical calculations: history windows exclude the current day.
CREATE TABLE mart_sales_daily AS
WITH history AS (
    SELECT f.*,
        count(*) OVER prior_7 AS history_7,
        count(*) OVER prior_28 AS history_28,
        avg(units) OVER prior_7 AS mean_7,
        avg(units) OVER prior_28 AS mean_28,
        lag(sell_price) OVER series AS previous_price
    FROM fact_sales_daily f
    WINDOW
        series AS (PARTITION BY store_id, item_id ORDER BY date),
        prior_7 AS (PARTITION BY store_id, item_id ORDER BY date
                    ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING),
        prior_28 AS (PARTITION BY store_id, item_id ORDER BY date
                     ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)
)
SELECT h.* EXCLUDE (history_7, history_28, mean_7, mean_28, previous_price),
    units * sell_price AS revenue_proxy,
    CASE WHEN history_7 = 7 THEN mean_7 END AS rolling_7d,
    CASE WHEN history_28 = 28 THEN mean_28 END AS rolling_28d,
    100.0 * (sell_price - previous_price) / nullif(previous_price, 0) AS price_change_pct,
    coalesce(history_28 = 28 AND mean_28 > 0 AND units > 2 * mean_28, FALSE) AS demand_spike_flag,
    date_diff('day', (SELECT max(date) FROM fact_sales_daily), CAST(? AS DATE)) AS data_freshness
FROM history h;
