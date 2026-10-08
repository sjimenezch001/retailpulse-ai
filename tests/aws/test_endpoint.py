import copy
import json

import pytest
from cloud.aws.contracts import canonical
from cloud.aws.lambda_handler import serve


def event(query="store=SYN_A"):
    return {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/metrics/units",
        "rawQueryString": query,
    }


def test_metric_loaded_not_hardcoded(s3, settings, inputs, reconciled):
    s3.objects[settings.key("serving", "units.json")] = canonical(reconciled)
    result = serve(event(), s3, settings, inputs[1])
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["value"] == 378 and data["metric"] == data["unit"] == "units"
    assert data["mode"] == "synthetic" and data["run_id"] == settings.run_id
    assert data["provenance"] == reconciled["provenance"]
    assert data["period"] == reconciled["period"]
    # A different valid artifact proves that implementation reads its actual value.
    changed = copy.deepcopy(reconciled)
    changed["stores"]["SYN_A"] += 1
    changed["total_units"] += 1
    s3.objects[settings.key("serving", "units.json")] = canonical(changed)
    assert json.loads(serve(event(), s3, settings, inputs[1])["body"])["value"] == 379


@pytest.mark.parametrize(
    "query",
    [
        "",
        "store=CA_1",
        "store=SYN_A&store=SYN_B",
        "store=SYN_A&sql=SELECT",
        "store=../../",
        "store=",
        "store=SYN_A%00",
        "store=" + "A" * 100,
    ],
)
def test_invalid_query_never_reads_s3(query, s3, settings, inputs):
    s3.denied = True
    assert serve(event(query), s3, settings, inputs[1])["statusCode"] == 400


@pytest.mark.parametrize(
    "failure", ["denied", "missing", "oversize", "malformed", "unreconciled", "stale"]
)
def test_metric_failures_are_safe(failure, s3, settings, inputs, reconciled):
    data = copy.deepcopy(reconciled)
    if failure == "denied":
        s3.denied = True
    elif failure == "oversize":
        s3.objects[settings.key("serving", "units.json")] = b"x" * 65537
    elif failure == "malformed":
        s3.objects[settings.key("serving", "units.json")] = b"not-json"
    elif failure in {"unreconciled", "stale"}:
        if failure == "stale":
            data["run_id"] = "1" * 24
        else:
            del data["reconciliation"]
        s3.objects[settings.key("serving", "units.json")] = canonical(data)
    result = serve(event(), s3, settings, inputs[1])
    assert result["statusCode"] == 503
    assert json.loads(result["body"]) == {"error": "metric_unavailable"}


def test_route_and_store_boundaries(s3, settings, inputs, reconciled):
    s3.objects[settings.key("serving", "units.json")] = canonical(reconciled)
    assert (
        serve(event("store=SYN_UNKNOWN"), s3, settings, inputs[1])["statusCode"] == 404
    )
    bad = event()
    bad["requestContext"]["http"]["method"] = "POST"
    assert serve(bad, s3, settings, inputs[1])["statusCode"] == 404
