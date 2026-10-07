# RP-04 gate — 2026-10-07

Status: CODE COMPLETE; REAL-DATA VALIDATION PENDING.

`python -m retailpulse silver` requires configured stores and departments and
a verified Bronze snapshot. pandas melts the selected series to daily sales;
calendar joins on `d` and weekly prices join on store/item/retail week with
explicit many-to-one validation. Missing prices retain sales and set
`price_missing`. No PySpark or new dependencies are introduced.

Outputs: `fact_sales_daily`, `dim_calendar`, `dim_product`, `dim_store`.
The fact key is date × store × item; dates are typed, units are nonnegative
integers. Duplicate keys are rejected, never arbitrarily deduplicated. Required
identifiers, product/store mappings, price references and daily calendar
continuity are validated. Source metadata is retained on the daily fact.
Unit totals and expected long-form counts reconcile with selected Bronze rows.

Content-addressed derived snapshots reference the Bronze run and sorted pilot
selection. Each Parquet output has a checksum. Quality failures occur before
publication; a previous good current pointer stays intact.

Synthetic gate validation:

- `python -m pytest -p no:cacheprovider`: `31 passed in 2.21s`.
- `python -m ruff check .`: `All checks passed!`.
- Coverage includes duplicates, invalid/negative/fractional/non-finite units,
  invalid dates, missing calendar keys, conflicting dimensions, invalid price
  references, missing prices, reproducibility, reconciliation and failed runs.

Real pilot selection, execution, scale and domain validation remain pending.
