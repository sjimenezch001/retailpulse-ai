"""Bounded versioned metric lookup, behind an AWS_IAM HTTP API route."""

import json
import os
import re
from importlib.resources import files
from urllib.parse import parse_qsl

from cloud.aws.contracts import (
    MAX_ARTIFACT_BYTES,
    LabError,
    bounded_read,
    validate_metric,
)
from cloud.aws.settings import Settings


def response(status, payload):
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json",
            "cache-control": "no-store",
        },
        "body": json.dumps(payload, allow_nan=False),
    }


def serve(event, s3, settings, trusted):
    context = event.get("requestContext", {}).get("http", {})
    if context.get("method") != "GET" or event.get("rawPath") != "/metrics/units":
        return response(404, {"error": "route_not_found"})
    raw = event.get("rawQueryString", "")
    if not isinstance(raw, str) or len(raw) > 80:
        return response(400, {"error": "invalid_query"})
    pairs = parse_qsl(raw, keep_blank_values=True)
    if (
        len(pairs) != 1
        or pairs[0][0] != "store"
        or not re.fullmatch(r"SYN_[A-Z0-9]{1,12}", pairs[0][1])
    ):
        return response(400, {"error": "invalid_store"})
    store = pairs[0][1]
    try:
        obj = s3.get_object(
            Bucket=settings.bucket,
            Key=settings.key("serving", "units.json"),
            ExpectedBucketOwner=settings.account,
        )
        data = json.loads(
            bounded_read(obj["Body"], obj["ContentLength"], MAX_ARTIFACT_BYTES)
        )
        metric = validate_metric(data, trusted, settings.run_id)
        if store not in metric["stores"]:
            return response(404, {"error": "store_not_found", "mode": "synthetic"})
        return response(
            200,
            {
                "mode": "synthetic",
                "notice": metric["notice"],
                "store": store,
                "period": metric["period"],
                "metric": "units",
                "unit": "units",
                "value": metric["stores"][store],
                "dataset_version": metric["dataset_version"],
                "run_id": metric["run_id"],
                "provenance": metric["provenance"],
            },
        )
    except (LabError, ValueError, TypeError, KeyError, OSError):
        return response(503, {"error": "metric_unavailable"})
    except Exception:
        # SDK exceptions are intentionally not reflected into responses or logs.
        return response(503, {"error": "metric_unavailable"})


def handler(event, context):
    import boto3
    from botocore.config import Config

    settings = Settings(
        os.environ["LAB_ACCOUNT"],
        os.environ["LAB_REGION"],
        os.environ["LAB_ENV"],
        os.environ["LAB_RUN_ID"],
    )
    trusted = json.loads(
        files("cloud.aws").joinpath("trusted_manifest.json").read_bytes()
    )
    client = boto3.client(
        "s3",
        region_name=settings.region,
        config=Config(
            connect_timeout=1,
            read_timeout=2,
            retries={"total_max_attempts": 1},
        ),
    )
    return serve(event, client, settings, trusted)
