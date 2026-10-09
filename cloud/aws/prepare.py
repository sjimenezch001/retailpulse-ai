"""Offline preparation: authenticated inputs, local reference and deterministic bundles."""

import importlib.metadata
import json
import zipfile
from datetime import date
from pathlib import Path

from cloud.aws.analytics import reference_queries
from cloud.aws.contracts import (
    LabError,
    canonical,
    digest,
    metric_reference,
    packaged_inputs,
    run_identity,
)

PACKAGE_FILES = (
    "cloud/__init__.py",
    "cloud/aws/__init__.py",
    "cloud/aws/contracts.py",
    "cloud/aws/settings.py",
)
SDK_DIRS = {"boto3", "botocore", "jmespath", "s3transfer", "dateutil", "urllib3"}


def code_digest(root):
    paths = sorted(
        [
            *Path(root, "cloud/aws").glob("*.py"),
            *Path(root, "cloud/aws/sql").glob("*.sql"),
            Path(root, "cloud/aws/requirements.txt"),
            *Path(root, "infra/aws").glob("*.tf"),
            *Path(root, "infra/aws").glob("*.tf.json"),
        ]
    )
    return digest(
        canonical(
            {
                p.relative_to(root).as_posix(): digest(
                    p.read_text(encoding="utf-8").encode()
                )
                for p in paths
            }
        )
    )


def write_zip(target, entries):
    if sum(map(len, entries.values())) > 250 * 1024 * 1024:
        raise LabError("bundle_uncompressed_limit")
    with zipfile.ZipFile(
        target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    if target.stat().st_size > 50 * 1024 * 1024:
        raise LabError("bundle_upload_limit")


def sdk_entries(root):
    vendor = Path(root) / "artifacts/rp12/sdk"
    expected = {}
    for line in (Path(root) / "cloud/aws/requirements.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            expected[name.replace("_", "-").lower()] = version
    actual = {
        dist.metadata["Name"].replace("_", "-").lower(): dist.version
        for dist in importlib.metadata.distributions(path=[str(vendor)])
    }
    if actual != expected:
        raise LabError("isolated_sdk_missing_or_unpinned")
    entries = {}
    for path in sorted(vendor.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(vendor)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        first = relative.parts[0]
        if (
            first not in SDK_DIRS
            and first != "six.py"
            and not first.endswith(".dist-info")
        ):
            continue
        if not path.resolve().is_relative_to(vendor.resolve()):
            raise LabError("sdk_path_escape")
        entries[relative.as_posix()] = path.read_bytes()
    return entries


def prepare(root):
    root = Path(root).resolve()
    out = root / "artifacts/rp12/prepared"
    out.mkdir(parents=True, exist_ok=True)
    blobs, trusted, tables = packaged_inputs(root)
    code = code_digest(root)
    run_id = run_identity(trusted, code)
    metric = metric_reference(tables, trusted, run_id)
    queries = reference_queries(tables)
    if int(queries["total_units"]["rows"][0][0]) != metric["total_units"]:
        raise LabError("independent_reference_mismatch")
    if {r[0]: int(r[1]) for r in queries["by_store"]["rows"]} != metric["stores"]:
        raise LabError("independent_store_mismatch")
    if sum(int(r[2]) for r in queries["dimension_join"]["rows"]) != metric["row_count"]:
        raise LabError("dimension_join_mismatch")
    for name, body in blobs.items():
        path = out / "input" / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(body)
    entries = {
        name: (root / name).read_text(encoding="utf-8").encode()
        for name in PACKAGE_FILES
    }
    entries["cloud/aws/trusted_manifest.json"] = canonical(trusted)
    entries.update(sdk_entries(root))
    write_zip(out / "glue_bundle.zip", entries)
    (out / "glue_job.py").write_text(
        (root / "cloud/aws/glue_job.py").read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    # Exercise local Parquet serialization only; this is explicitly not a Spark/Glue run.
    import pyarrow as pa
    import pyarrow.parquet as pq

    local_parquet = out / "local_reference_parquet"
    local_parquet.mkdir(exist_ok=True)
    for name, rows in tables.items():
        typed = [
            {
                k: date.fromisoformat(v)
                if k
                in {
                    "date",
                    "first_sales_date",
                    "last_sales_date",
                    "as_of_date",
                }
                else v
                for k, v in row.items()
            }
            for row in rows
        ]
        table = pa.Table.from_pylist(typed)
        pq.write_table(table, local_parquet / f"{name}.parquet")
        if pq.read_table(local_parquet / f"{name}.parquet").to_pylist() != typed:
            raise LabError("local_parquet_roundtrip")
    uploads = [
        *(f"input/{name}" for name in sorted(blobs)),
        "glue_job.py",
        "glue_bundle.zip",
    ]
    record = {
        "mode": "synthetic",
        "run_id": run_id,
        "code_digest": code,
        "input_bytes": sum(map(len, blobs.values())),
        "metric_reference": metric,
        "query_reference": queries,
        "files": {name: digest((out / name).read_bytes()) for name in uploads},
        "spark_executed": False,
        "aws_executed": False,
    }
    (out / "prepared.json").write_bytes(canonical(record) + b"\n")
    return record


def load_prepared(root):
    root = Path(root)
    out = root / "artifacts/rp12/prepared"
    try:
        record = json.loads((out / "prepared.json").read_bytes())
        _, trusted, tables = packaged_inputs(root)
        code = code_digest(root)
        run_id = run_identity(trusted, code)
        if record["code_digest"] != code or record["run_id"] != run_id:
            raise LabError("prepared_code_stale")
        if record["metric_reference"] != metric_reference(tables, trusted, run_id):
            raise LabError("prepared_reference_changed")
        if record["query_reference"] != reference_queries(tables):
            raise LabError("prepared_sql_reference_changed")
        expected_files = {
            *(f"input/{n}" for n in ["manifest.json", *(f"{t}.csv" for t in tables)]),
            "glue_job.py",
            "glue_bundle.zip",
        }
        if set(record["files"]) != expected_files:
            raise LabError("prepared_file_allowlist")
        for name, checksum in record["files"].items():
            if digest((out / name).read_bytes()) != checksum:
                raise LabError("prepared_bundle_changed")
        return record
    except (OSError, KeyError, ValueError) as exc:
        raise LabError("prepare_required_or_changed") from exc
