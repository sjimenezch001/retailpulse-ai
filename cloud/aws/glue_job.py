"""Glue 5.0 / Spark 3.5 batch entry point; never executed by offline validation."""

import json
from datetime import date
from importlib.resources import files

from cloud.aws.contracts import (
    INPUT_FILES,
    MAX_INPUT_BYTES,
    SCHEMAS,
    TABLES,
    LabError,
    bounded_read,
    canonical,
    metric_reference,
    run_identity,
    validate_inputs,
)
from cloud.aws.settings import Settings


def read_inputs(s3, settings, trusted):
    blobs = {}
    remaining = MAX_INPUT_BYTES
    for name in sorted(INPUT_FILES):
        obj = s3.get_object(
            Bucket=settings.bucket,
            Key=settings.key("input", name),
            ExpectedBucketOwner=settings.account,
        )
        content = bounded_read(obj["Body"], obj["ContentLength"], remaining)
        remaining -= len(content)
        blobs[name] = content
    return validate_inputs(blobs, trusted)


def spark_tables(spark, tables):
    from pyspark.sql.types import (
        BooleanType,
        DateType,
        DoubleType,
        LongType,
        StringType,
        StructField,
        StructType,
    )

    kinds = {
        "string": StringType,
        "long": LongType,
        "double": DoubleType,
        "date": DateType,
        "boolean": BooleanType,
    }
    frames = {}
    for table in TABLES:
        schema = SCHEMAS[table]
        explicit = StructType(
            [
                StructField(
                    name,
                    kinds[kind](),
                    name
                    in {
                        "sell_price",
                        "revenue_proxy",
                        "rolling_7d",
                        "rolling_28d",
                        "price_change_pct",
                    },
                )
                for name, kind in schema
            ]
        )
        rows = [
            tuple(
                date.fromisoformat(row[name]) if kind == "date" else row[name]
                for name, kind in schema
            )
            for row in tables[table]
        ]
        frames[table] = spark.createDataFrame(rows, explicit)
    return frames


def reconcile_spark(frames, expected):
    from pyspark.sql import functions as F

    facts = frames["mart_sales_daily"]
    if facts.count() != expected["row_count"]:
        raise LabError("spark_row_count")
    if (
        facts.groupBy("date", "store_id", "item_id")
        .count()
        .filter("count != 1")
        .count()
    ):
        raise LabError("spark_duplicate_keys")
    if facts.filter(
        F.col("date").isNull() | F.col("units").isNull() | (F.col("units") < 0)
    ).count():
        raise LabError("spark_invalid_fact")
    for name, key in (("dim_store", "store_id"), ("dim_product", "item_id")):
        if frames[name].groupBy(key).count().filter("count != 1").count():
            raise LabError("spark_dimension_key")
    joined = facts.join(frames["dim_store"], "store_id").join(
        frames["dim_product"], "item_id"
    )
    if joined.count() != expected["row_count"]:
        raise LabError("spark_join_multiplication")
    aggregation = facts.groupBy("store_id").agg(F.sum("units").alias("units"))
    actual = {r["store_id"]: r["units"] for r in aggregation.collect()}
    if actual != expected["stores"]:
        raise LabError("spark_aggregate_mismatch")
    return aggregation


def execute(s3, settings, trusted, code_digest, spark):
    """Fixed run prefix + overwrite of partial runs; completed runs are verified."""
    if run_identity(trusted, code_digest) != settings.run_id:
        raise LabError("job_run_identity")
    tables = read_inputs(s3, settings, trusted)
    expected = metric_reference(tables, trusted, settings.run_id)
    frames = spark_tables(spark, tables)
    aggregates = reconcile_spark(frames, expected)
    base = f"s3://{settings.bucket}/{settings.prefix('curated')}"
    marker_key = settings.key("curated", "_complete.json")
    try:
        marker = s3.get_object(
            Bucket=settings.bucket,
            Key=marker_key,
            ExpectedBucketOwner=settings.account,
        )
    except Exception as exc:
        if getattr(exc, "response", {}).get("Error", {}).get("Code") not in {
            "NoSuchKey",
            "404",
        }:
            raise LabError("completion_check_denied_or_unavailable") from exc
        complete = False
    else:
        data = json.loads(bounded_read(marker["Body"], marker["ContentLength"], 65536))
        if data != {"run_id": settings.run_id, "metric": expected}:
            raise LabError("completion_mismatch")
        complete = True
    if not complete:
        for name, frame in frames.items():
            frame.coalesce(1).write.mode("overwrite").parquet(base + name + "/")
        aggregates.coalesce(1).write.mode("overwrite").parquet(base + "store_units/")
    # Read back actual Parquet, including on reruns. A marker alone is insufficient.
    persisted = {
        name: spark.read.schema(frame.schema).parquet(base + name + "/")
        for name, frame in frames.items()
    }
    reconcile_spark(persisted, expected)
    for name, source in frames.items():
        if (
            source.exceptAll(persisted[name]).count()
            or persisted[name].exceptAll(source).count()
        ):
            raise LabError("parquet_logical_mismatch")
    saved_aggregate = spark.read.schema(aggregates.schema).parquet(
        base + "store_units/"
    )
    if (
        aggregates.exceptAll(saved_aggregate).count()
        or saved_aggregate.exceptAll(aggregates).count()
    ):
        raise LabError("parquet_aggregate_mismatch")
    if not complete:
        for filename, payload in (
            ("_metric_candidate.json", expected),
            ("_complete.json", {"run_id": settings.run_id, "metric": expected}),
        ):
            s3.put_object(
                Bucket=settings.bucket,
                Key=settings.key("curated", filename),
                Body=canonical(payload),
                ContentType="application/json",
                ServerSideEncryption="AES256",
                ExpectedBucketOwner=settings.account,
            )
    # Only query-checks may publish serving/ after actual Athena reconciliation.
    return {
        "mode": "synthetic",
        "run_id": settings.run_id,
        "reused": complete,
        "row_count": expected["row_count"],
        "units": expected["total_units"],
    }


def main():
    import sys

    import boto3
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions
    from botocore.config import Config
    from pyspark.context import SparkContext

    args = getResolvedOptions(
        sys.argv,
        [
            "JOB_NAME",
            "LAB_ACCOUNT",
            "LAB_REGION",
            "LAB_ENV",
            "LAB_RUN_ID",
            "CODE_DIGEST",
        ],
    )
    settings = Settings(
        args["LAB_ACCOUNT"], args["LAB_REGION"], args["LAB_ENV"], args["LAB_RUN_ID"]
    )
    trusted = json.loads(
        files("cloud.aws").joinpath("trusted_manifest.json").read_bytes()
    )
    context = GlueContext(SparkContext.getOrCreate())
    context.spark_session.conf.set("spark.sql.session.timeZone", "UTC")
    job = Job(context)
    job.init(args["JOB_NAME"], args)
    s3 = boto3.client(
        "s3",
        region_name=settings.region,
        config=Config(
            connect_timeout=3,
            read_timeout=10,
            retries={"total_max_attempts": 1},
        ),
    )
    report = execute(s3, settings, trusted, args["CODE_DIGEST"], context.spark_session)
    print(json.dumps(report))
    job.commit()


if __name__ == "__main__":
    main()
