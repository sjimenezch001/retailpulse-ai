SELECT store_id, sum(units) AS units FROM mart_sales_daily GROUP BY store_id ORDER BY store_id;
