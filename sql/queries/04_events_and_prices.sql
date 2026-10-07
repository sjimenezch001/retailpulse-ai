-- Q4: associations only; this query cannot establish causality.
SELECT m.date, m.store_id, m.dept_id, m.item_id,
       c.event_name_1, c.event_name_2, m.units, m.rolling_28d,
       m.price_change_pct, m.demand_spike_flag
FROM mart_sales_daily m JOIN dim_calendar c USING (date)
WHERE c.event_name_1 IS NOT NULL OR c.event_name_2 IS NOT NULL
   OR m.price_change_pct != 0 OR m.demand_spike_flag
ORDER BY date, store_id, item_id;
