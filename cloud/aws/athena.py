"""Six fixed read-only queries, bounded polling/results, cancellation and reconciliation."""

import json
import time

from cloud.aws.analytics import QUERY_NAMES, query_text
from cloud.aws.contracts import (
    MAX_ARTIFACT_BYTES,
    LabError,
    bounded_read,
    canonical,
    digest,
    validate_metric,
)


class Queries:
    def __init__(self, client, settings, *, sleep=time.sleep, clock=time.monotonic):
        self.client, self.settings = client, settings
        self.sleep, self.clock = sleep, clock

    def check_workgroup(self):
        cfg = self.client.get_work_group(WorkGroup=self.settings.name)["WorkGroup"][
            "Configuration"
        ]
        result = cfg.get("ResultConfiguration", {})
        if (
            cfg.get("EnforceWorkGroupConfiguration") is not True
            or cfg.get("BytesScannedCutoffPerQuery") != 10_485_760
            or result.get("OutputLocation") != f"s3://{self.settings.bucket}/results/"
            or result.get("ExpectedBucketOwner") != self.settings.account
            or result.get("EncryptionConfiguration", {}).get("EncryptionOption")
            != "SSE_S3"
        ):
            raise LabError("unsafe_athena_workgroup")

    def run(self, name):
        sql = query_text(name)  # Reject untrusted query names before touching a client.
        self.check_workgroup()
        query_id = None
        terminal = False
        try:
            start = self.client.start_query_execution(
                QueryString=sql,
                QueryExecutionContext={
                    "Database": self.settings.database,
                    "Catalog": "AwsDataCatalog",
                },
                WorkGroup=self.settings.name,
                ClientRequestToken=digest(
                    canonical([self.settings.lab_id, self.settings.run_id, name, sql])
                ),
                ResultConfiguration={
                    "OutputLocation": f"s3://{self.settings.bucket}/results/",
                    "ExpectedBucketOwner": self.settings.account,
                    "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
                },
                ResultReuseConfiguration={
                    "ResultReuseByAgeConfiguration": {"Enabled": False}
                },
            )
            query_id = start["QueryExecutionId"]
            deadline = self.clock() + 60
            for _ in range(30):
                execution = self.client.get_query_execution(
                    QueryExecutionId=query_id,
                )["QueryExecution"]
                state = execution["Status"]["State"]
                if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                    terminal = True
                    if state != "SUCCEEDED":
                        raise LabError("athena_query_failed")
                    break
                if state not in {"QUEUED", "RUNNING"} or self.clock() >= deadline:
                    raise LabError("athena_query_timeout_or_state")
                self.sleep(2)
            else:
                raise LabError("athena_query_timeout")
            if execution.get("WorkGroup") != self.settings.name:
                raise LabError("query_workgroup_mismatch")
            result = self.client.get_query_results(
                QueryExecutionId=query_id,
                MaxResults=1000,
                QueryResultType="DATA_ROWS",
            )
            if result.get("NextToken"):
                raise LabError("athena_result_limit")
            rs = result["ResultSet"]
            columns = [c["Name"] for c in rs["ResultSetMetadata"]["ColumnInfo"]]
            rows = [[c.get("VarCharValue") for c in row["Data"]] for row in rs["Rows"]]
            if (
                not rows
                or rows[0] != columns
                or any(len(row) != len(columns) for row in rows)
            ):
                raise LabError("athena_result_shape")
            stats = execution.get("Statistics", {})
            if stats.get("DataScannedInBytes", 0) > 10_485_760:
                raise LabError("athena_scan_limit")
            return {
                "result": {"columns": columns, "rows": rows[1:]},
                "query_id": query_id,
                "scanned_bytes": stats.get("DataScannedInBytes"),
                "execution_ms": stats.get("EngineExecutionTimeInMillis"),
            }
        except LabError:
            raise
        except Exception as exc:
            raise LabError("athena_denied_or_unavailable") from exc
        finally:
            if query_id and not terminal:
                try:
                    self.client.stop_query_execution(QueryExecutionId=query_id)
                except Exception as exc:
                    raise LabError("athena_cancellation_unverified") from exc


def read_json(s3, settings, category, filename):
    obj = s3.get_object(
        Bucket=settings.bucket,
        Key=settings.key(category, filename),
        ExpectedBucketOwner=settings.account,
    )
    return json.loads(
        bounded_read(obj["Body"], obj["ContentLength"], MAX_ARTIFACT_BYTES)
    )


def reconcile_and_publish(queries, s3, settings, trusted, prepared):
    expected = prepared["metric_reference"]
    complete = read_json(s3, settings, "curated", "_complete.json")
    candidate = read_json(s3, settings, "curated", "_metric_candidate.json")
    validate_metric(candidate, trusted, settings.run_id, require_reconciled=False)
    if candidate != expected or complete != {
        "run_id": settings.run_id,
        "metric": expected,
    }:
        raise LabError("glue_candidate_not_reconciled")
    actual = {}
    for name in QUERY_NAMES:
        actual[name] = queries.run(name)
        if actual[name]["result"] != prepared["query_reference"][name]:
            raise LabError("athena_reference_mismatch")
    final = {
        **candidate,
        "reconciliation": {
            "engine": "athena",
            "checks": list(QUERY_NAMES),
            "query_ids": [actual[name]["query_id"] for name in QUERY_NAMES],
        },
    }
    validate_metric(final, trusted, settings.run_id)
    s3.put_object(
        Bucket=settings.bucket,
        Key=settings.key("serving", "units.json"),
        Body=canonical(final),
        ContentType="application/json",
        ServerSideEncryption="AES256",
        ExpectedBucketOwner=settings.account,
    )
    return {
        "mode": "synthetic",
        "live": True,
        "run_id": settings.run_id,
        "queries": actual,
    }
