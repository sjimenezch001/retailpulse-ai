import copy

import pytest
from cloud.aws.analytics import QUERY_NAMES, query_text
from cloud.aws.athena import Queries, reconcile_and_publish
from cloud.aws.contracts import LabError, canonical


class StubAthena:
    """All identifiers/statistics below are synthetic test stubs, never cloud evidence."""

    def __init__(self, settings, prepared):
        self.settings, self.prepared = settings, prepared
        self.started, self.stopped = [], []
        self.state, self.extra_page = "SUCCEEDED", False
        self.cfg = {
            "EnforceWorkGroupConfiguration": True,
            "BytesScannedCutoffPerQuery": 10_485_760,
            "ResultConfiguration": {
                "OutputLocation": f"s3://{settings.bucket}/results/",
                "ExpectedBucketOwner": settings.account,
                "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
            },
        }

    def get_work_group(self, **args):
        assert args["WorkGroup"] == self.settings.name
        return {"WorkGroup": {"Configuration": self.cfg}}

    def start_query_execution(self, **args):
        name = next(n for n in QUERY_NAMES if query_text(n) == args["QueryString"])
        assert args["QueryExecutionContext"]["Database"] == self.settings.database
        assert args["WorkGroup"] == self.settings.name
        assert args["ResultConfiguration"] == self.cfg["ResultConfiguration"]
        self.started.append(name)
        return {"QueryExecutionId": "stub-" + name.replace("_", "-")}

    def get_query_execution(self, **args):
        return {
            "QueryExecution": {
                "WorkGroup": self.settings.name,
                "Status": {"State": self.state},
                "Statistics": {
                    "DataScannedInBytes": 456,
                    "EngineExecutionTimeInMillis": 12,
                },
            }
        }

    def get_query_results(self, **args):
        name = args["QueryExecutionId"].removeprefix("stub-").replace("-", "_")
        ref = self.prepared["query_reference"][name]
        result = {
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [{"Name": n} for n in ref["columns"]]
                },
                "Rows": [
                    {"Data": [{} if v is None else {"VarCharValue": v} for v in row]}
                    for row in [ref["columns"], *ref["rows"]]
                ],
            }
        }
        if self.extra_page:
            result["NextToken"] = "stub-more"
        return result

    def stop_query_execution(self, **args):
        self.stopped.append(args["QueryExecutionId"])


def test_suite_reconciles_then_publishes(settings, inputs, prepared, s3):
    expected = prepared["metric_reference"]
    for name, value in (
        ("_complete.json", {"run_id": settings.run_id, "metric": expected}),
        ("_metric_candidate.json", expected),
    ):
        s3.objects[settings.key("curated", name)] = canonical(value)
    api = StubAthena(settings, prepared)
    result = reconcile_and_publish(
        Queries(api, settings),
        s3,
        settings,
        inputs[1],
        prepared,
    )
    assert api.started == list(QUERY_NAMES)
    assert len(result["queries"]) == 6 and len(s3.writes) == 1
    assert s3.writes[0]["Key"] == settings.key("serving", "units.json")
    assert s3.writes[0]["ServerSideEncryption"] == "AES256"
    assert all(r["scanned_bytes"] == 456 for r in result["queries"].values())


def test_mismatch_never_publishes(settings, inputs, prepared, s3):
    expected = prepared["metric_reference"]
    s3.objects[settings.key("curated", "_complete.json")] = canonical(
        {"run_id": settings.run_id, "metric": expected}
    )
    s3.objects[settings.key("curated", "_metric_candidate.json")] = canonical(expected)
    bad = copy.deepcopy(prepared)
    bad["query_reference"]["total_units"]["rows"] = [["999"]]
    api = StubAthena(settings, bad)
    with pytest.raises(LabError, match="reference_mismatch"):
        reconcile_and_publish(Queries(api, settings), s3, settings, inputs[1], prepared)
    assert not s3.writes


def test_incomplete_etl_never_queries(settings, inputs, prepared, s3):
    s3.objects[settings.key("curated", "_complete.json")] = canonical({})
    s3.objects[settings.key("curated", "_metric_candidate.json")] = canonical(
        prepared["metric_reference"]
    )
    api = StubAthena(settings, prepared)
    with pytest.raises(LabError):
        reconcile_and_publish(Queries(api, settings), s3, settings, inputs[1], prepared)
    assert not api.started and not s3.writes


def test_timeout_cancels_one_query(settings, prepared):
    api = StubAthena(settings, prepared)
    api.state = "RUNNING"
    with pytest.raises(LabError, match="timeout"):
        Queries(api, settings, sleep=lambda seconds: None).run("total_units")
    assert len(api.started) == len(api.stopped) == 1


@pytest.mark.parametrize("state", ["FAILED", "CANCELLED", "unexpected"])
def test_terminal_failures_and_unknown_state(settings, prepared, state):
    api = StubAthena(settings, prepared)
    api.state = state
    with pytest.raises(LabError):
        Queries(api, settings).run("total_units")
    assert len(api.stopped) == (1 if state == "unexpected" else 0)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda cfg: cfg.update(EnforceWorkGroupConfiguration=False),
        lambda cfg: cfg.update(BytesScannedCutoffPerQuery=0),
        lambda cfg: cfg["ResultConfiguration"].update(
            OutputLocation="s3://unapproved/"
        ),
        lambda cfg: cfg["ResultConfiguration"].update(
            ExpectedBucketOwner="999999999999"
        ),
        lambda cfg: cfg["ResultConfiguration"]["EncryptionConfiguration"].update(
            EncryptionOption="NONE"
        ),
    ],
)
def test_unsafe_workgroup_never_submits(settings, prepared, mutation):
    api = StubAthena(settings, prepared)
    mutation(api.cfg)
    with pytest.raises(LabError, match="unsafe_athena"):
        Queries(api, settings).run("total_units")
    assert not api.started


def test_no_untrusted_sql_or_unbounded_results(settings, prepared):
    api = StubAthena(settings, prepared)
    with pytest.raises(LabError, match="allowlisted"):
        Queries(api, settings).run("DROP DATABASE anything")
    assert not api.started
    api.extra_page = True
    with pytest.raises(LabError, match="result_limit"):
        Queries(api, settings).run("total_units")


def test_request_failure_cancels_without_leaking_error(settings, prepared):
    api = StubAthena(settings, prepared)

    def denied(**kwargs):
        raise RuntimeError("stub private exception detail")

    api.get_query_execution = denied
    with pytest.raises(LabError, match="denied_or_unavailable") as error:
        Queries(api, settings).run("total_units")
    assert "private exception" not in str(error.value)
    assert len(api.stopped) == 1
