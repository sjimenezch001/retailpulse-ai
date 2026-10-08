"""Closed synthetic input contract shared by preparation, Glue and Lambda.

Only the repository-approved manifest is trusted. A manifest fetched from S3
cannot authorize a new dataset. No forecast observations are uploaded.
"""

import csv
import hashlib
import io
import json
import math
import re
from datetime import date
from pathlib import Path

MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024
MAX_ROWS = 10_000
TABLES = ("mart_sales_daily", "dim_store", "dim_product", "pipeline_metadata")
INPUT_FILES = frozenset(["manifest.json", *(f"{t}.csv" for t in TABLES)])
VERSION = "synthetic-web-v1"
NOTICE = "Synthetic laboratory data; no real M5 or measured model performance."
SCHEMAS = {
    "mart_sales_daily": (
        ("item_id", "string"),
        ("store_id", "string"),
        ("dept_id", "string"),
        ("cat_id", "string"),
        ("state_id", "string"),
        ("pipeline_run_id", "string"),
        ("ingestion_ts", "string"),
        ("source_checksum", "string"),
        ("d", "string"),
        ("units", "long"),
        ("date", "date"),
        ("wm_yr_wk", "long"),
        ("sell_price", "double"),
        ("price_missing", "boolean"),
        ("revenue_proxy", "double"),
        ("rolling_7d", "double"),
        ("rolling_28d", "double"),
        ("price_change_pct", "double"),
        ("demand_spike_flag", "boolean"),
        ("data_freshness", "long"),
    ),
    "dim_store": (("store_id", "string"), ("state_id", "string")),
    "dim_product": (
        ("item_id", "string"),
        ("dept_id", "string"),
        ("cat_id", "string"),
    ),
    "pipeline_metadata": (
        ("gold_run_id", "string"),
        ("silver_run_id", "string"),
        ("bronze_run_id", "string"),
        ("first_sales_date", "date"),
        ("last_sales_date", "date"),
        ("as_of_date", "date"),
        ("source_ingestion_ts", "string"),
        ("generated_at", "string"),
        ("identity_json", "string"),
    ),
}
NULLABLE = {
    "sell_price",
    "revenue_proxy",
    "rolling_7d",
    "rolling_28d",
    "price_change_pct",
}


class LabError(ValueError):
    """Safe, categorical error; never include credentials or remote response bodies."""


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def bounded_read(body, size, limit):
    try:
        if not isinstance(size, int) or not 0 <= size <= limit:
            raise LabError("object_size_limit")
        content = body.read(limit + 1)
        if len(content) != size or len(content) > limit:
            raise LabError("object_size_mismatch")
        return content
    finally:
        body.close()


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise LabError("invalid_date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LabError("invalid_date") from exc


def parse_cell(name, kind, value):
    if value == "":
        if name not in NULLABLE:
            raise LabError("required_value_missing")
        return None
    try:
        if kind == "long":
            if not re.fullmatch(r"\d+", value):
                raise LabError("invalid_integer")
            result = int(value)
            if result > 2**53 - 1:
                raise LabError("integer_out_of_range")
            return result
        if kind == "double":
            result = float(value)
            if not math.isfinite(result):
                raise LabError("nonfinite_value")
            if name != "price_change_pct" and result < 0:
                raise LabError("negative_value")
            return result
        if kind == "boolean":
            if value not in ("True", "False"):
                raise LabError("invalid_boolean")
            return value == "True"
        if kind == "date":
            iso_date(value)
        if not value or len(value) > 1024:
            raise LabError("invalid_text")
        return value
    except (TypeError, ValueError) as exc:
        raise LabError("invalid_cell") from exc


def parse_csv(content, table):
    schema = SCHEMAS[table]
    reader = csv.DictReader(io.StringIO(content.decode("utf-8"), newline=""))
    if reader.fieldnames != [name for name, _ in schema]:
        raise LabError("schema_mismatch")
    rows = []
    for raw in reader:
        if len(rows) >= MAX_ROWS or set(raw) != {name for name, _ in schema}:
            raise LabError("row_limit_or_schema")
        rows.append({name: parse_cell(name, kind, raw[name]) for name, kind in schema})
    if not rows:
        raise LabError("empty_table")
    return rows


def unique(rows, columns):
    keys = [tuple(row[c] for c in columns) for row in rows]
    if len(keys) != len(set(keys)):
        raise LabError("duplicate_key")


def validate_inputs(blobs, trusted):
    if set(blobs) != INPUT_FILES or sum(map(len, blobs.values())) > MAX_INPUT_BYTES:
        raise LabError("input_allowlist_or_size")
    try:
        manifest = json.loads(blobs["manifest.json"])
    except (ValueError, UnicodeError) as exc:
        raise LabError("invalid_manifest") from exc
    if manifest != trusted or manifest.get("mode") != "synthetic":
        raise LabError("unapproved_manifest")
    if manifest.get("version") != VERSION:
        raise LabError("unapproved_dataset_version")
    tables = {}
    for name in TABLES:
        content = blobs[f"{name}.csv"]
        if digest(content) != trusted["sha256"][name]:
            raise LabError("input_checksum_mismatch")
        tables[name] = parse_csv(content, name)
    facts, stores, products, meta = (tables[n] for n in TABLES)
    unique(facts, ("date", "store_id", "item_id"))
    unique(stores, ("store_id",))
    unique(products, ("item_id",))
    if len(meta) != 1 or meta[0]["gold_run_id"] != VERSION:
        raise LabError("metadata_mismatch")
    if any(
        not meta[0][n].startswith("synthetic-")
        for n in ("gold_run_id", "silver_run_id", "bronze_run_id")
    ):
        raise LabError("non_synthetic_provenance")
    store_map = {r["store_id"]: r for r in stores}
    product_map = {r["item_id"]: r for r in products}
    for row in [*facts, *stores, *products]:
        for name in ("item_id", "store_id", "dept_id", "cat_id", "state_id"):
            if name in row and not re.fullmatch(r"SYN_[A-Z0-9]+", row[name]):
                raise LabError("non_synthetic_dimension")
    for row in facts:
        store = store_map.get(row["store_id"])
        product = product_map.get(row["item_id"])
        if not store or not product or row["state_id"] != store["state_id"]:
            raise LabError("dimension_reference")
        if any(row[k] != product[k] for k in ("dept_id", "cat_id")):
            raise LabError("dimension_reference")
        if row["pipeline_run_id"] != "synthetic-fixture":
            raise LabError("non_synthetic_provenance")
        if not re.fullmatch(r"[0-9a-f]{64}", row["source_checksum"]):
            raise LabError("source_provenance")
        if row["price_missing"] != (row["sell_price"] is None):
            raise LabError("price_null_semantics")
        if row["sell_price"] is None:
            if row["revenue_proxy"] is not None:
                raise LabError("revenue_null_semantics")
        elif row["revenue_proxy"] is None or not math.isclose(
            row["revenue_proxy"], row["units"] * row["sell_price"], abs_tol=1e-9
        ):
            raise LabError("revenue_formula")
    dates = sorted({r["date"] for r in facts})
    if (dates[0], dates[-1]) != (
        meta[0]["first_sales_date"],
        meta[0]["last_sales_date"],
    ):
        raise LabError("period_mismatch")
    elapsed = (iso_date(meta[0]["as_of_date"]) - iso_date(dates[-1])).days
    if elapsed < 0 or any(r["data_freshness"] != elapsed for r in facts):
        raise LabError("freshness_mismatch")
    return tables


def packaged_inputs(root):
    directory = Path(root) / "src/retailpulse/api/synthetic"
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if manifest.get("mode") != "synthetic" or manifest.get("version") != VERSION:
        raise LabError("unapproved_package")
    total = (directory / "manifest.json").stat().st_size
    # Verify every packaged table, including excluded simulated forecasts.
    for name, checksum in manifest["sha256"].items():
        if not re.fullmatch(r"[a-z_]+", name):
            raise LabError("package_path")
        path = directory / f"{name}.csv"
        if path.resolve().parent != directory.resolve():
            raise LabError("package_path")
        total += path.stat().st_size
        if total > MAX_INPUT_BYTES or digest(path.read_bytes()) != checksum:
            raise LabError("package_integrity_or_size")
    blobs = {name: (directory / name).read_bytes() for name in INPUT_FILES}
    return blobs, manifest, validate_inputs(blobs, manifest)


def run_identity(trusted, code_digest):
    if not re.fullmatch(r"[0-9a-f]{64}", code_digest):
        raise LabError("invalid_code_digest")
    return digest(
        canonical(
            {
                "dataset_version": trusted["version"],
                "inputs": {t: trusted["sha256"][t] for t in TABLES},
                "code_sha256": code_digest,
                "contract": "aws-lab-v1",
            }
        )
    )[:24]


def metric_reference(tables, trusted, run_id):
    if not re.fullmatch(r"[0-9a-f]{24}", run_id):
        raise LabError("invalid_run_identity")
    facts = tables["mart_sales_daily"]
    stores = {
        row["store_id"]: sum(
            f["units"] for f in facts if f["store_id"] == row["store_id"]
        )
        for row in tables["dim_store"]
    }
    return {
        "mode": "synthetic",
        "notice": NOTICE,
        "dataset_version": trusted["version"],
        "run_id": run_id,
        "metric": "units",
        "unit": "units",
        "period": {
            "start": min(r["date"] for r in facts),
            "end": max(r["date"] for r in facts),
        },
        "row_count": len(facts),
        "total_units": sum(stores.values()),
        "stores": stores,
        "provenance": {
            "source": "repository-packaged synthetic CSVs",
            "input_sha256": {t: trusted["sha256"][t] for t in TABLES},
            "grain": "date x store_id x item_id",
        },
    }


def validate_metric(value, trusted, run_id, require_reconciled=True):
    required = {
        "mode",
        "notice",
        "dataset_version",
        "run_id",
        "metric",
        "unit",
        "period",
        "row_count",
        "total_units",
        "stores",
        "provenance",
    }
    if set(value) not in (required, required | {"reconciliation"}):
        raise LabError("metric_schema")
    if (
        value["mode"],
        value["dataset_version"],
        value["run_id"],
        value["metric"],
        value["unit"],
        value["notice"],
    ) != ("synthetic", trusted["version"], run_id, "units", "units", NOTICE):
        raise LabError("metric_identity")
    provenance = value["provenance"]
    if provenance != {
        "source": "repository-packaged synthetic CSVs",
        "input_sha256": {t: trusted["sha256"][t] for t in TABLES},
        "grain": "date x store_id x item_id",
    }:
        raise LabError("metric_provenance")
    if set(value["period"]) != {"start", "end"} or (
        iso_date(value["period"]["start"]) > iso_date(value["period"]["end"])
    ):
        raise LabError("metric_period")
    stores = value["stores"]
    if not isinstance(stores, dict) or not 1 <= len(stores) <= 10:
        raise LabError("metric_stores")
    if any(
        not re.fullmatch(r"SYN_[A-Z0-9]+", name)
        or type(units) is not int
        or not 0 <= units <= 2**53 - 1
        for name, units in stores.items()
    ):
        raise LabError("metric_values")
    if type(value["row_count"]) is not int or not 0 < value["row_count"] <= MAX_ROWS:
        raise LabError("metric_row_count")
    if type(value["total_units"]) is not int or value["total_units"] != sum(
        stores.values()
    ):
        raise LabError("metric_total")
    if require_reconciled:
        rec = value.get("reconciliation", {})
        if (
            set(rec) != {"engine", "checks", "query_ids"}
            or rec["engine"] != "athena"
            or rec["checks"]
            != [
                "total_units",
                "by_store",
                "by_date",
                "dimension_join",
                "quality",
                "row_counts",
            ]
            or not isinstance(rec["query_ids"], list)
            or len(rec["query_ids"]) != 6
            or any(
                not isinstance(q, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,128}", q)
                for q in rec["query_ids"]
            )
        ):
            raise LabError("metric_not_reconciled")
    return value
