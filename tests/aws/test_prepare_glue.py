import json
import shutil
import zipfile
from types import SimpleNamespace

import pytest
from cloud.aws import glue_job
from cloud.aws import prepare as preparation
from cloud.aws.contracts import SCHEMAS, LabError, canonical, run_identity
from cloud.aws.settings import Settings


def test_offline_preparation_is_repeatable_and_rejects_tampering(
    root, tmp_path, monkeypatch
):
    shutil.copytree(
        root / "cloud", tmp_path / "cloud", ignore=shutil.ignore_patterns("__pycache__")
    )
    target = tmp_path / "src/retailpulse/api/synthetic"
    target.parent.mkdir(parents=True)
    shutil.copytree(root / "src/retailpulse/api/synthetic", target)
    monkeypatch.setattr(
        preparation,
        "sdk_entries",
        lambda root: {"stub-sdk.txt": b"offline packaging stub"},
    )
    first = preparation.prepare(tmp_path)
    second = preparation.prepare(tmp_path)
    assert first == second and first["metric_reference"]["total_units"] == 1386
    assert first["spark_executed"] is False and first["aws_executed"] is False
    out = tmp_path / "artifacts/rp12/prepared"
    with zipfile.ZipFile(out / "lambda.zip") as bundle:
        assert "cloud/aws/trusted_manifest.json" in bundle.namelist()
        assert not any(
            name.endswith((".duckdb", ".pbix", ".mp4", ".csv"))
            for name in bundle.namelist()
        )
    assert preparation.load_prepared(tmp_path) == first
    (out / "input/dim_store.csv").write_text("unapproved")
    with pytest.raises(LabError):
        preparation.load_prepared(tmp_path)


def test_catalog_schema_matches_actual_transform(root):
    catalog = json.loads((root / "infra/aws/catalog.tf.json").read_text())["locals"][
        "table_columns"
    ]
    kinds = {
        "string": "string",
        "long": "bigint",
        "date": "date",
        "double": "double",
        "boolean": "boolean",
    }
    for table, schema in SCHEMAS.items():
        assert catalog[table] == [
            {"name": name, "type": kinds[kind]} for name, kind in schema
        ]
    assert catalog["store_units"] == [
        {"name": "store_id", "type": "string"},
        {"name": "units", "type": "bigint"},
    ]


def test_glue_publication_rerun_orchestration_with_spark_stub(inputs, s3, monkeypatch):
    """Tests publication control only; never claims native Spark/Glue execution."""
    blobs, trusted, tables = inputs
    code = "0" * 64
    settings = Settings(
        "000000000000", "sa-east-1", "offline", run_identity(trusted, code)
    )
    for name, body in blobs.items():
        s3.objects[settings.key("input", name)] = body
    stored, writes = {}, []

    class Frame:
        schema = "stub-explicit-schema"

        def __init__(self, logical):
            self.logical = logical

        def coalesce(self, count):
            assert count == 1
            return self

        @property
        def write(self):
            return self

        def mode(self, value):
            assert value == "overwrite"  # Never append on a fixed-grain run.
            return self

        def parquet(self, path):
            assert path.startswith(
                f"s3://{settings.bucket}/{settings.prefix('curated')}"
            )
            stored[path] = self
            writes.append(path)

        def exceptAll(self, other):
            return SimpleNamespace(
                count=lambda: 0 if self.logical == other.logical else 1
            )

    frames = {name: Frame(rows) for name, rows in tables.items()}
    aggregation = Frame("stub aggregation")
    monkeypatch.setattr(glue_job, "spark_tables", lambda spark, data: frames)
    monkeypatch.setattr(
        glue_job, "reconcile_spark", lambda frames, expected: aggregation
    )
    spark = SimpleNamespace(
        read=SimpleNamespace(
            schema=lambda schema: SimpleNamespace(parquet=lambda path: stored[path])
        )
    )
    first = glue_job.execute(s3, settings, trusted, code, spark)
    second = glue_job.execute(s3, settings, trusted, code, spark)
    assert first["reused"] is False and second["reused"] is True
    assert first["units"] == second["units"] == 1386
    assert len(writes) == 5 and len(s3.writes) == 2
    assert not any("/serving/" in call["Key"] for call in s3.writes)
    marker = json.loads(s3.objects[settings.key("curated", "_complete.json")])
    marker["run_id"] = "f" * 24
    s3.objects[settings.key("curated", "_complete.json")] = canonical(marker)
    with pytest.raises(LabError, match="completion_mismatch"):
        glue_job.execute(s3, settings, trusted, code, spark)


def test_glue_downloads_only_bounded_allowlisted_inputs(inputs, settings, s3):
    blobs, trusted, _ = inputs
    for name, body in blobs.items():
        s3.objects[settings.key("input", name)] = body
    assert len(glue_job.read_inputs(s3, settings, trusted)["mart_sales_daily"]) == 252
    s3.objects[settings.key("input", "mart_sales_daily.csv")] = b"x" * (
        10 * 1024 * 1024 + 1
    )
    with pytest.raises(LabError, match="size"):
        glue_job.read_inputs(s3, settings, trusted)
