"""Security regressions with fake state, service responses and HTTP transport."""

import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from cloud.aws.contracts import LabError
from cloud.aws.endpoint_check import smoke_test
from cloud.aws.ownership import stop_workloads, verify_state


def test_foreign_state_id_cannot_hide_behind_expected_name(settings, outputs):
    values = {"bucket": settings.bucket, "id": settings.bucket, "tags": settings.tags}
    resource = {"type": "aws_s3_bucket", "mode": "managed", "values": values}
    state = {"values": {"root_module": {"resources": [resource]}}}
    assert verify_state(state, settings, outputs)
    values["id"] = "another-bucket"
    with pytest.raises(LabError, match="foreign"):
        verify_state(state, settings, outputs)


@pytest.mark.parametrize(
    "kind", ["aws_instance", "aws_nat_gateway", "aws_s3_bucket_unknown"]
)
def test_unexpected_state_resources_rejected(settings, outputs, kind):
    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": kind,
                        "mode": "managed",
                        "values": {"id": settings.bucket, "bucket": settings.bucket},
                    }
                ]
            }
        }
    }
    with pytest.raises(LabError, match="foreign"):
        verify_state(state, settings, outputs)


def test_empty_or_nested_state_is_not_cleanup_evidence(settings, outputs):
    for root in ({}, {"resources": []}, {"child_modules": [{}], "resources": [{}]}):
        with pytest.raises(LabError):
            verify_state({"values": {"root_module": root}}, settings, outputs)


def test_cleanup_waits_for_jobs_and_queries_to_stop(settings):
    calls = []
    glue = SimpleNamespace(
        get_job_runs=lambda **kw: {
            "JobRuns": [{"Id": "stub-job", "JobRunState": "RUNNING"}]
        },
        batch_stop_job_run=lambda **kw: calls.append("stop-job") or {"Errors": []},
        get_job_run=lambda **kw: {"JobRun": {"JobRunState": "STOPPED"}},
    )
    queries = iter(["RUNNING", "CANCELLED"])
    athena = SimpleNamespace(
        list_query_executions=lambda **kw: {"QueryExecutionIds": ["stub-query"]},
        get_query_execution=lambda **kw: {
            "QueryExecution": {
                "WorkGroup": settings.name,
                "Status": {"State": next(queries)},
            }
        },
        stop_query_execution=lambda **kw: calls.append("stop-query"),
    )
    result = stop_workloads(
        {"glue": glue, "athena": athena}, settings, sleep=lambda _: None
    )
    assert result == {"stopped_job_runs": 1, "stopped_queries": 1}
    assert calls == ["stop-job", "stop-query"]


def test_cleanup_cannot_proceed_when_job_stop_not_confirmed(settings):
    glue = SimpleNamespace(
        get_job_runs=lambda **kw: {
            "JobRuns": [{"Id": "stub-job", "JobRunState": "RUNNING"}]
        },
        batch_stop_job_run=lambda **kw: {"Errors": [{"ErrorDetail": "stub denial"}]},
    )
    with pytest.raises(LabError, match="job_stop_unverified"):
        stop_workloads(
            {"glue": glue, "athena": object()}, settings, sleep=lambda _: None
        )


def endpoint_outputs(settings, outputs):
    return {
        **outputs,
        "api_id": "stubapi",
        "endpoint": "https://stubapi.execute-api.sa-east-1.amazonaws.com",
        "function": settings.name + "-metrics",
        "lambda_role": settings.name + "-metrics",
        "log_groups": [
            *outputs["log_groups"],
            f"/aws/lambda/{settings.name}-metrics",
            f"/retailpulse/{settings.environment}/api",
        ],
    }


def test_smoke_rejects_unsigned_then_reconciles_signed_stub(settings, outputs, metric):
    calls = []
    payload = {
        **metric,
        "store": "SYN_A",
        "value": metric["stores"]["SYN_A"],
        "metric": "units",
        "unit": "units",
    }
    response = io.BytesIO(json.dumps(payload).encode())
    response.status = 200

    def open_request(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 403, "stub denial", {}, io.BytesIO())
        assert request.get_header("Authorization") == "stub-signed"
        return response

    result = smoke_test(
        None,
        settings,
        endpoint_outputs(settings, outputs),
        metric,
        opener=SimpleNamespace(open=open_request),
        signer=lambda *args: {"Authorization": "stub-signed"},
    )
    assert result["value"] == 378 and len(calls) == 2
    # Stub result describes control flow; this test is not evidence of a live API.


def test_smoke_rejects_anonymous_success_before_signing(settings, outputs, metric):
    def must_not_sign(*args):
        pytest.fail("Anonymous success must fail before signing")

    with pytest.raises(LabError, match="unsigned_request"):
        smoke_test(
            None,
            settings,
            endpoint_outputs(settings, outputs),
            metric,
            opener=SimpleNamespace(open=lambda *a, **kw: io.BytesIO(b"")),
            signer=must_not_sign,
        )
