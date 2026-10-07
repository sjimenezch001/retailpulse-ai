-- Q3: becomes populated by RP-06; empty until a baseline run exists.
SELECT model, split, horizon, count(*) AS observations,
       sum(predicted_units) AS predicted_units,
       sum(actual_units) AS actual_units,
       sum(abs(actual_units - predicted_units)) / nullif(sum(abs(actual_units)), 0) AS WMAPE,
       avg(abs(actual_units - predicted_units)) AS MAE,
       sqrt(avg(pow(actual_units - predicted_units, 2))) AS RMSE
FROM fact_forecast
WHERE actual_units IS NOT NULL
GROUP BY model, split, horizon ORDER BY model, split, horizon;
