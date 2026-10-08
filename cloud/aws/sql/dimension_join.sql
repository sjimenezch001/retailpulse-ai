SELECT s.store_id, s.state_id, count(*) AS fact_rows, sum(f.units) AS units
FROM mart_sales_daily f
JOIN dim_store s ON f.store_id = s.store_id
JOIN dim_product p ON f.item_id = p.item_id
GROUP BY s.store_id, s.state_id ORDER BY s.store_id, s.state_id;
