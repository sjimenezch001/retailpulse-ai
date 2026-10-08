"""Allowlisted SQL and independent local DuckDB reconciliation."""

from pathlib import Path

from cloud.aws.contracts import SCHEMAS, LabError

QUERY_NAMES = (
    "total_units",
    "by_store",
    "by_date",
    "dimension_join",
    "quality",
    "row_counts",
)


def query_text(name):
    if name not in QUERY_NAMES:
        raise LabError("query_not_allowlisted")
    return (Path(__file__).parent / "sql" / f"{name}.sql").read_text(encoding="utf-8")


def reference_queries(tables):
    # Optional local-only analytical dependency; never imported in Lambda or Glue.
    import duckdb

    kinds = {
        "string": "VARCHAR",
        "long": "BIGINT",
        "double": "DOUBLE",
        "date": "DATE",
        "boolean": "BOOLEAN",
    }
    with duckdb.connect(":memory:", config={"enable_external_access": False}) as db:
        for table in ("mart_sales_daily", "dim_store", "dim_product"):
            schema = SCHEMAS[table]
            columns = ",".join(f'"{name}" {kinds[kind]}' for name, kind in schema)
            db.execute(f'CREATE TABLE "{table}" ({columns})')
            db.executemany(
                f'INSERT INTO "{table}" VALUES ({",".join("?" for _ in schema)})',
                [[row[name] for name, _ in schema] for row in tables[table]],
            )
        results = {}
        for name in QUERY_NAMES:
            result = db.execute(query_text(name))
            results[name] = {
                "columns": [d[0] for d in result.description],
                "rows": [
                    [None if v is None else str(v) for v in row]
                    for row in result.fetchall()
                ],
            }
        return results
