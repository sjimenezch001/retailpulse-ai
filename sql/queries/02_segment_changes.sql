-- Q2: last 7 observed days versus previous 7, by store and department.
WITH bounds AS (SELECT max(date) AS last_date FROM mart_sales_daily)
SELECT store_id, dept_id,
       sum(CASE WHEN date > last_date - INTERVAL 7 DAY THEN units ELSE 0 END) AS current_units,
       sum(CASE WHEN date <= last_date - INTERVAL 7 DAY THEN units ELSE 0 END) AS previous_units,
       current_units - previous_units AS units_change
FROM mart_sales_daily CROSS JOIN bounds
WHERE date > last_date - INTERVAL 14 DAY
GROUP BY store_id, dept_id ORDER BY abs(units_change) DESC, store_id, dept_id;
