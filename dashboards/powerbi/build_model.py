"""Generate a portable TOM model specification from the checked BI schemas."""
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[2]
NAMES = {"date": "Date", "week": "Week", "store": "Store", "department": "Department",
         "product": "Product", "model": "Model", "split": "Split", "demand_level": "Demand",
         "horizon": "Horizon", "sales_daily": "SalesDaily", "sales_product_week": "SalesProductWeekly",
         "forecast": "Forecast", "metadata": "Snapshot"}
LABELS = {"date": "Date", "week_key": "WeekKey", "week_start": "Week Start", "week_end": "Week End",
          "year": "Year", "month": "Month", "year_month": "Year Month", "weekday": "Weekday",
          "event_context": "Event Context", "store_id": "Store", "state_id": "State",
          "dept_id": "Department", "item_id": "Product", "cat_id": "Category",
          "model": "ModelKey", "model_name": "Model", "split": "Split", "demand_level": "Demand Level",
          "horizon": "Horizon", "units": "Units", "known_revenue_proxy": "Known Revenue",
          "observation_count": "Observations", "priced_count": "Priced Observations",
          "rolling_7d_units": "Rolling7", "rolling_28d_units": "Rolling28", "spike_count": "Spikes",
          "price_change_sum": "Price Change Sum", "price_change_count": "Price Change Count",
          "event_units": "Event Units", "snap_units": "SNAP Units", "forecast_origin": "Forecast Origin",
          "target_date": "Target Date", "predicted_units": "Predicted Units", "actual_units": "Actual Units",
          "absolute_error": "Absolute Error", "squared_error": "Squared Error", "signed_error": "Signed Error",
          "data_freshness": "Freshness Days", "last_sales_date": "Last Sales Date",
          "first_sales_date": "First Sales Date", "as_of_date": "As Of Date"}
MEASURES = []


def measure(name, dax, sql, meaning, source, *, fmt="#,0", filters="Date, store and department.", nulls="BLANK when no observations match."):
    MEASURES.append({"name": name, "expression": dax, "formatString": fmt,
                     "description": meaning, "sql": sql, "source": source,
                     "filters": filters, "nulls": nulls})


measure("Total Units", "SUM(SalesDaily[Units])", "SELECT sum(units) FROM bi_sales_daily", "Observed units in the selected daily period.", "mart_sales_daily.units")
measure("Sales Observations", "SUM(SalesDaily[Observations])", "SELECT sum(observation_count) FROM bi_sales_daily", "Underlying item/store/day count.", "mart_sales_daily")
measure("Priced Observations", "SUM(SalesDaily[Priced Observations])", "SELECT sum(priced_count) FROM bi_sales_daily", "Observations with a known price, including zero sales.", "mart_sales_daily.sell_price")
measure("Known Revenue Proxy", "SUM(SalesDaily[Known Revenue])", "SELECT sum(revenue_proxy) FROM mart_sales_daily", "Partial units-times-price sum for known prices; not audited revenue.", "mart_sales_daily.revenue_proxy", fmt="#,0.00", nulls="Unknown prices are excluded; all unknown is BLANK, never zero-filled.")
measure("Price Coverage", "DIVIDE([Priced Observations], [Sales Observations])", "SELECT count(sell_price)::DOUBLE/nullif(count(*),0) FROM mart_sales_daily", "Share of observations with known prices.", "mart_sales_daily.sell_price", fmt="0.0%", nulls="BLANK for an empty denominator.")
measure("Canonical Revenue Proxy", "IF([Sales Observations] = [Priced Observations], [Known Revenue Proxy])", "SELECT CASE WHEN count(sell_price)=count(*) THEN sum(revenue_proxy) END FROM mart_sales_daily", "Conservative canonical revenue: unknown if any price is missing.", "mart_sales_daily.revenue_proxy", fmt="#,0.00", nulls="BLANK whenever any included price is unknown.")
measure("Revenue Proxy Completeness", 'IF(ISBLANK([Sales Observations]), "No observations", IF([Sales Observations] = [Priced Observations], "Complete price coverage", "Partial: missing prices"))', "SELECT CASE WHEN count(*)=0 THEN 'No observations' WHEN count(sell_price)=count(*) THEN 'Complete price coverage' ELSE 'Partial: missing prices' END FROM mart_sales_daily", "Readable completeness disclosure beside known-price partial revenue.", "mart_sales_daily.sell_price", fmt="", nulls="Displays No observations for an empty selection.")
for days in (7, 28):
    measure(f"Rolling {days}D Demand", f"AVERAGEX(VALUES('Date'[Date]), CALCULATE(SUM(SalesDaily[Rolling{days}])))", f"SELECT avg(demand) FROM (SELECT date,sum(rolling_{days}d) demand FROM mart_sales_daily GROUP BY date)", "Sum across series, then average across selected dates; never add rolling values across dates.", f"mart_sales_daily.rolling_{days}d", fmt="#,0.0", nulls="Incomplete-history dates remain BLANK and are excluded from the date average.")
measure("Previous Period Units", "VAR StartDate = MIN('Date'[Date]) VAR Days = INT(MAX('Date'[Date]) - StartDate) + 1 RETURN CALCULATE([Total Units], REMOVEFILTERS('Date'), DATESBETWEEN('Date'[Date], StartDate - Days, StartDate - 1))", "SELECT sum(units) FROM mart_sales_daily WHERE date BETWEEN $start - ($end-$start+1) AND $start - 1", "Units in the immediately preceding equal-length daily interval.", "mart_sales_daily.units", filters="Replaces the date filter; preserves store and department. Use a contiguous date range.")
period_sql = "WITH periods AS (SELECT sum(units) FILTER(WHERE date BETWEEN $start AND $end) current_units, sum(units) FILTER(WHERE date BETWEEN $start - ($end-$start+1) AND $start - 1) previous_units FROM mart_sales_daily) "
measure("Period-over-Period Change", "IF(NOT ISBLANK([Previous Period Units]) && NOT ISBLANK([Total Units]), [Total Units] - [Previous Period Units])", period_sql + "SELECT current_units - previous_units FROM periods", "Absolute unit change versus the preceding equal-length interval.", "mart_sales_daily.units")
measure("Period-over-Period Change %", "DIVIDE([Period-over-Period Change], [Previous Period Units])", period_sql + "SELECT (current_units-previous_units)/nullif(previous_units,0) FROM periods", "Relative unit change versus the preceding period.", "mart_sales_daily.units", fmt="+0.0%;-0.0%;0.0%", nulls="BLANK for missing or zero previous-period units.")
measure("Demand Spike Count", "SUM(SalesDaily[Spikes])", "SELECT count(*) FROM mart_demand_alerts", "Item/store/day flags from the canonical heuristic, not confirmed causal events.", "mart_sales_daily.demand_spike_flag")
measure("Data Freshness", "MAX(Snapshot[Freshness Days])", "SELECT date_diff('day',last_sales_date,as_of_date) FROM pipeline_metadata", "Days from last observed sales to the Gold as_of date; independent of refresh time.", "pipeline_metadata", fmt='#,0 "days"', filters="Global snapshot, unaffected by segment or date filters.")

product_filters = "Observed-week range, store, department and product; each selected week includes all its observed days. Daily Date does not filter this fact."
for name, column, sql, meaning, fmt in [
    ("Product Units", "Units", "sum(units)", "Observed units over selected whole weeks.", "#,0"),
    ("Product Spike Count", "Spikes", "sum(spike_count)", "Canonical spike flags in selected product-weeks.", "#,0"),
    ("Event-period Units", "Event Units", "sum(event_units)", "Units observed on event days; descriptive association only.", "#,0"),
    ("SNAP-period Units", "SNAP Units", "sum(snap_units)", "Units observed on state SNAP days; descriptive association only.", "#,0")]:
    measure(name, f"SUM(SalesProductWeekly[{column}])", f"SELECT {sql} FROM bi_sales_product_week", meaning, "mart_sales_daily joined to dim_calendar", fmt=fmt, filters=product_filters)
measure("Product Price Coverage", "DIVIDE(SUM(SalesProductWeekly[Priced Observations]),SUM(SalesProductWeekly[Observations]))", "SELECT sum(priced_count)::DOUBLE/nullif(sum(observation_count),0) FROM bi_sales_product_week", "Price coverage for selected products and observed weeks.", "mart_sales_daily.sell_price", fmt="0.0%", filters=product_filters)
measure("Average Price Change %", "DIVIDE(SUM(SalesProductWeekly[Price Change Sum]),SUM(SalesProductWeekly[Price Change Count])) / 100", "SELECT sum(price_change_sum)/nullif(sum(price_change_count),0)/100 FROM bi_sales_product_week", "Mean of valid daily Gold price changes; noncausal, not a period price return.", "mart_sales_daily.price_change_pct", fmt="+0.00%;-0.00%;0.00%", filters=product_filters, nulls="Undefined daily changes are excluded; BLANK when none are valid.")
for direction, title in [("DESC", "Top Product Units"), ("ASC", "Bottom Product Units")]:
    measure(title, f"VAR Demand = [Product Units] VAR Position = RANKX(FILTER(ALLSELECTED(Product[Product]), CALCULATE([Product Units]) > 0), [Product Units], , {direction}, DENSE) RETURN IF(Demand > 0 && Position <= 10, Demand)", f"SELECT item_id,sum(units) AS units FROM bi_sales_product_week GROUP BY item_id HAVING sum(units)>0 QUALIFY dense_rank() OVER(ORDER BY sum(units) {direction})<=10 ORDER BY units {direction},item_id", "First ten positive-demand ranks; includes ties, zero-demand products are excluded.", "mart_sales_daily.units", filters=product_filters, nulls="Nonpositive demand and ranks beyond ten return BLANK.")

forecast_filters = "Target date, store, department, product, model, split, horizon and origin-derived demand level. No sales fact joins."
measure("Forecast Observations", "COUNTROWS(Forecast)", "SELECT count(*) FROM bi_forecast", "Number of scored model/series/day predictions.", "fact_forecast", filters=forecast_filters)
measure("Actual Units", "SUMX(SUMMARIZE(Forecast, Forecast[Forecast Origin], Forecast[Target Date], Forecast[Store], Forecast[Product], Forecast[Split], \"Observed\", MAX(Forecast[Actual Units])), [Observed])", "SELECT sum(actual) FROM (SELECT forecast_origin,target_date,store_id,item_id,split,max(actual_units) actual FROM bi_forecast GROUP BY ALL)", "Observed units counted once per series/date/split even if several models are selected.", "fact_forecast.actual_units", filters=forecast_filters)
measure("Predicted Units", "IF(HASONEVALUE('Model'[ModelKey]),SUM(Forecast[Predicted Units]))", "SELECT sum(predicted_units) FROM bi_forecast WHERE model=$model", "Forecast units for the single selected model.", "fact_forecast.predicted_units", filters=forecast_filters, nulls="BLANK unless exactly one model is selected; forecasts from different models are never added together.")
measure("WMAPE", "DIVIDE(SUM(Forecast[Absolute Error]),SUM(Forecast[Actual Units]))", "SELECT sum(absolute_error)/nullif(sum(abs(actual_units)),0) FROM bi_forecast", "Canonical ratio of summed absolute error to actual units; never an average of segment WMAPEs.", "fact_forecast", fmt="0.00%", filters=forecast_filters, nulls="BLANK for a zero actual-unit denominator.")
measure("MAE", "DIVIDE(SUM(Forecast[Absolute Error]),[Forecast Observations])", "SELECT avg(absolute_error) FROM bi_forecast", "Mean absolute error in units.", "fact_forecast", fmt="0.000", filters=forecast_filters)
measure("RMSE", "VAR MSE = DIVIDE(SUM(Forecast[Squared Error]),[Forecast Observations]) RETURN IF(NOT ISBLANK(MSE), SQRT(MSE))", "SELECT sqrt(avg(squared_error)) FROM bi_forecast", "Root mean squared error in units.", "fact_forecast", fmt="0.000", filters=forecast_filters)
measure("Forecast Bias", "DIVIDE(SUM(Forecast[Signed Error]),SUM(Forecast[Actual Units]))", "SELECT sum(predicted_units-actual_units)/nullif(sum(actual_units),0) FROM bi_forecast", "Signed relative bias; positive is overprediction.", "fact_forecast", fmt="+0.0%;-0.0%;0.0%", filters=forecast_filters, nulls="BLANK for zero actual units.")
measure("Forecast versus Actual Variance", "IF(HASONEVALUE('Model'[ModelKey]),[Predicted Units] - [Actual Units])", "SELECT sum(predicted_units)-sum(actual_units) FROM bi_forecast WHERE model=$model", "Absolute forecast-minus-actual unit difference for the selected model.", "fact_forecast", fmt="+#,0;-#,0;0", filters=forecast_filters, nulls="BLANK for multiple or no models.")
for metric, sql_expression in {"WMAPE": "sum(absolute_error)/nullif(sum(abs(actual_units)),0)", "MAE": "avg(absolute_error)", "RMSE": "sqrt(avg(squared_error))"}.items():
    measure(f"Comparison {metric}", f"CALCULATE([{metric}], REMOVEFILTERS('Model'), TREATAS(VALUES(ComparisonModel[ModelKey]),'Model'[ModelKey]))", f"SELECT model, {sql_expression} FROM bi_forecast GROUP BY model", "All-model benchmark, retaining the other selected filters.", "fact_forecast", fmt="0.00%" if metric == "WMAPE" else "0.000", filters="Comparison model replaces the model selector; all other forecast filters remain active.")
measure("Rolling Mean WMAPE", 'CALCULATE([WMAPE], REMOVEFILTERS(\'Model\'), \'Model\'[ModelKey] = "rolling_mean")', "SELECT sum(absolute_error)/nullif(sum(abs(actual_units)),0) FROM bi_forecast WHERE model='rolling_mean'", "Rolling-mean benchmark on the same selected backtest observations.", "fact_forecast", fmt="0.00%", filters="Replaces only the model filter; all other forecast filters remain active.", nulls="BLANK for no observations or zero actual units.")


def identifier(name):
    return str(uuid5(NAMESPACE_URL, "retailpulse-bi/" + name))


def build():
    manifest = json.loads((ROOT / "artifacts/powerbi/data/manifest.json").read_text(encoding="utf-8"))
    tables = []
    for source, spec in manifest["tables"].items():
        name = NAMES[source]
        columns, m_types = [], []
        for column in spec["columns"]:
            key, sql_type = column["name"], column["type"]
            kind, m_type = ("dateTime", "type date") if sql_type == "DATE" else ("int64", "Int64.Type") if "INT" in sql_type else ("double", "type number") if sql_type in ("DOUBLE", "FLOAT") else ("string", "type text")
            label = LABELS.get(key, key)
            col = {"name": label, "dataType": kind, "sourceColumn": key, "summarizeBy": "none",
                   "lineageTag": identifier(name + "/" + label)}
            if kind == "dateTime":
                col["formatString"] = "yyyy-MM-dd"
            if name == "Date" and key == "date":
                col["isKey"] = True
            if name in ("Week", "Product", "Model") and key in ("week_key", "dept_id", "model"):
                col["isHidden"] = True
            columns.append(col)
            m_types.append('{"' + key + '", ' + m_type + '}')
        m = f'''let
    Source = Csv.Document(File.Contents(DataFolder & "/{spec['file']}"), [Delimiter=",", Columns={len(columns)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{{", ".join(m_types)}}}, "en-US")
in Typed'''
        tables.append({"name": name, "lineageTag": identifier(name), "isHidden": source.startswith("sales_") or source in ("forecast", "metadata"),
                       "columns": columns, "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": m}}]})
    comparison = json.loads(json.dumps(next(table for table in tables if table["name"] == "Model")))
    comparison["name"] = "ComparisonModel"
    comparison["lineageTag"] = identifier("ComparisonModel")
    comparison["partitions"][0]["name"] = "ComparisonModel"
    for column in comparison["columns"]:
        column["lineageTag"] = identifier("ComparisonModel/" + column["name"])
    tables.append(comparison)
    tables.append({"name": "Metrics", "columns": [{"name": "Value", "dataType": "int64", "sourceColumn": "Value", "isHidden": True}],
                   "partitions": [{"name": "Metrics", "mode": "import", "source": {"type": "m", "expression": '#table(type table [Value = Int64.Type], {{0}})'}}],
                   "measures": [{key: value for key, value in m.items() if key in ("name", "expression", "formatString", "description")} | {"lineageTag": identifier("Metrics/" + m["name"])} for m in MEASURES]})
    relations = []
    for fact, column, dimension, key in [
        ("SalesDaily", "Date", "Date", "Date"), ("SalesDaily", "Store", "Store", "Store"), ("SalesDaily", "Department", "Department", "Department"),
        ("SalesProductWeekly", "WeekKey", "Week", "WeekKey"), ("SalesProductWeekly", "Store", "Store", "Store"), ("SalesProductWeekly", "Product", "Product", "Product"),
        ("Product", "Department", "Department", "Department"),
        ("Forecast", "Target Date", "Date", "Date"), ("Forecast", "Store", "Store", "Store"), ("Forecast", "Product", "Product", "Product"),
        ("Forecast", "ModelKey", "Model", "ModelKey"), ("Forecast", "Split", "Split", "Split"),
        ("Forecast", "Horizon", "Horizon", "Horizon"), ("Forecast", "Demand Level", "Demand", "Demand Level")]:
        relations.append({"name": identifier(f"{fact}/{column}/{dimension}"), "fromTable": fact, "fromColumn": column,
                          "toTable": dimension, "toColumn": key, "fromCardinality": "many", "toCardinality": "one",
                          "crossFilteringBehavior": "oneDirection"})
    database = {"name": "RetailPulse", "id": "RetailPulse", "compatibilityLevel": 1600,
                "model": {"culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3", "discourageImplicitMeasures": True,
                          "expressions": [{"name": "DataFolder", "kind": "m", "expression": '\"\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]'}],
                          "tables": tables, "relationships": relations}}
    target = ROOT / "artifacts/rp08-tools/model.json"
    target.write_text(json.dumps(database, indent=2) + "\n", encoding="utf-8")
    model_dir = ROOT / "dashboards/powerbi/RetailPulse.SemanticModel"
    model_dir.mkdir(exist_ok=True)
    (model_dir / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2) + "\n", encoding="utf-8")
    docs = ["# Power BI measure contract", "", "All SQL examples apply the same filter predicates and grains as their DAX context. `bi_*` views are defined by `sql/bi/serving.sql`. Revenue is a proxy, not audited financial revenue. Weekly diagnostics select whole observed weeks. Forecast metrics use backtests only.", ""]
    for m in MEASURES:
        docs += ["## " + m["name"], "", "```dax", m["expression"], "```", "", m["description"], "",
                 "Gold source: `" + m["source"] + "`.", "", "Filters: " + m["filters"], "", "Missing values: " + m["nulls"], "", "SQL verification:", "", "```sql", m["sql"] + ";", "```", ""]
    (ROOT / "dashboards/powerbi/measures.md").write_text("\n".join(docs), encoding="utf-8")
    print(f"Generated {len(tables)} tables, {len(relations)} relationships, {len(MEASURES)} measures.")


if __name__ == "__main__":
    build()
