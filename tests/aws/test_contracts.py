import copy
import csv
import io
import json

import pytest
from cloud.aws.analytics import reference_queries
from cloud.aws.contracts import (
    MAX_INPUT_BYTES,
    LabError,
    bounded_read,
    canonical,
    digest,
    parse_cell,
    run_identity,
    validate_inputs,
    validate_metric,
)


def test_independent_totals_nulls_and_grain(inputs, metric):
    blobs, trusted, tables = inputs
    assert sum(map(len, blobs.values())) < MAX_INPUT_BYTES
    assert metric["total_units"] == 1386 and metric["stores"]["SYN_A"] == 378
    assert metric["row_count"] == 252
    assert metric["period"] == {"start": "2020-01-01", "end": "2020-02-11"}
    facts = tables["mart_sales_daily"]
    missing = [r for r in facts if r["price_missing"]]
    assert missing and all(
        r["sell_price"] is None and r["revenue_proxy"] is None for r in missing
    )
    assert len({(r["date"], r["store_id"], r["item_id"]) for r in facts}) == len(facts)
    queries = reference_queries(tables)
    assert queries["total_units"]["rows"] == [["1386"]]
    assert queries["by_store"]["rows"][0] == ["SYN_A", "378"]
    assert sum(int(r[1]) for r in queries["by_date"]["rows"]) == 1386
    assert sum(int(r[2]) for r in queries["dimension_join"]["rows"]) == 252
    assert sum(int(r[3]) for r in queries["dimension_join"]["rows"]) == 1386
    assert trusted["mode"] == "synthetic"


@pytest.mark.parametrize(
    "mutation", ["extra", "missing", "hash", "manifest", "oversize"]
)
def test_closed_input_allowlist(inputs, mutation):
    blobs, trusted, _ = inputs
    blobs = blobs.copy()
    if mutation == "extra":
        blobs["real_m5.csv"] = b"unapproved"
    elif mutation == "missing":
        del blobs["dim_store.csv"]
    elif mutation == "hash":
        blobs["mart_sales_daily.csv"] += b"\n"
    elif mutation == "oversize":
        blobs["mart_sales_daily.csv"] = b"x" * (MAX_INPUT_BYTES + 1)
    else:
        fake = copy.deepcopy(trusted)
        fake["mode"] = "real"
        blobs["manifest.json"] = canonical(fake)
    with pytest.raises(LabError):
        validate_inputs(blobs, trusted)


def altered_facts(inputs, mutate):
    blobs, trusted, _ = inputs
    blobs, trusted = blobs.copy(), copy.deepcopy(trusted)
    reader = csv.DictReader(io.StringIO(blobs["mart_sales_daily.csv"].decode()))
    rows = list(reader)
    mutate(rows)
    content = io.StringIO(newline="")
    writer = csv.DictWriter(content, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    blobs["mart_sales_daily.csv"] = content.getvalue().encode()
    # Test the logical contract separately from its prior integrity gate.
    trusted["sha256"]["mart_sales_daily"] = digest(blobs["mart_sales_daily.csv"])
    blobs["manifest.json"] = canonical(trusted)
    return blobs, trusted


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows.append(rows[0].copy()),
        lambda rows: rows[0].update(store_id="CA_1"),
        lambda rows: rows[0].update(units="-1"),
        lambda rows: rows[0].update(date="2020-02-31"),
        lambda rows: rows[0].update(revenue_proxy="0"),
        lambda rows: rows[0].update(dept_id="SYN_WRONG"),
        lambda rows: rows[0].update(pipeline_run_id="real-m5"),
        lambda rows: rows[0].update(rolling_7d="NaN"),
        lambda rows: rows[0].update(data_freshness="0"),
    ],
)
def test_invalid_logical_facts_rejected(inputs, mutation):
    blobs, trusted = altered_facts(inputs, mutation)
    with pytest.raises(LabError):
        validate_inputs(blobs, trusted)


@pytest.mark.parametrize(
    "name,kind,value",
    [
        ("units", "long", "1.5"),
        ("units", "long", "9007199254740992"),
        ("price_missing", "boolean", "false"),
        ("sell_price", "double", "inf"),
        ("sell_price", "double", "-1"),
        ("date", "date", "2020/01/01"),
    ],
)
def test_explicit_types(name, kind, value):
    with pytest.raises(LabError):
        parse_cell(name, kind, value)


def test_read_limit_and_body_close():
    stream = io.BytesIO(b"1234")
    with pytest.raises(LabError):
        bounded_read(stream, 4, 3)
    assert stream.closed
    stream = io.BytesIO(b"12345")
    with pytest.raises(LabError):
        bounded_read(stream, 3, 8)
    assert stream.closed


def test_run_identity_changes_only_with_contract_sources(inputs):
    trusted = inputs[1]
    assert run_identity(trusted, "0" * 64) == run_identity(
        copy.deepcopy(trusted), "0" * 64
    )
    assert run_identity(trusted, "1" * 64) != run_identity(trusted, "0" * 64)
    with pytest.raises(LabError):
        run_identity(trusted, "untrusted")


def test_reconciliation_required(inputs, metric, reconciled, settings):
    with pytest.raises(LabError, match="not_reconciled"):
        validate_metric(metric, inputs[1], settings.run_id)
    assert validate_metric(reconciled, inputs[1], settings.run_id) == reconciled
    forged = json.loads(json.dumps(reconciled))
    forged["provenance"]["input_sha256"] = {}
    with pytest.raises(LabError, match="provenance"):
        validate_metric(forged, inputs[1], settings.run_id)
