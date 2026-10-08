SELECT 'dim_product' AS table_name, count(*) AS row_count FROM dim_product
UNION ALL SELECT 'dim_store', count(*) FROM dim_store
UNION ALL SELECT 'mart_sales_daily', count(*) FROM mart_sales_daily
ORDER BY table_name;
