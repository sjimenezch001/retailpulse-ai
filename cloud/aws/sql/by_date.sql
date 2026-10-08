SELECT date, sum(units) AS units FROM mart_sales_daily GROUP BY date ORDER BY date;
