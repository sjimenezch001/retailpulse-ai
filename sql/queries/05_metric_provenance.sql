-- Q5: canonical definition, table/period and source snapshot metadata.
SELECT d.*, 'mart_sales_daily' AS source_table,
       p.first_sales_date, p.last_sales_date, p.as_of_date,
       p.silver_run_id, p.bronze_run_id, p.source_ingestion_ts, p.generated_at
FROM metric_definitions d CROSS JOIN pipeline_metadata p
ORDER BY metric;
