import copy
import json

import pytest
from cloud.aws.contracts import LabError, canonical, digest
from cloud.aws.foundations import bucket_policy_equivalent, verify_bucket_security
from cloud.aws.policies import bucket_policy


@pytest.mark.parametrize("reverse", [False, True])
def test_only_same_arn_singleton_representation_is_equivalent(settings, reverse):
    expected = bucket_policy(settings)
    actual = copy.deepcopy(expected)
    for statement in actual["Statement"]:
        if len(statement["Resource"]) == 1:
            statement["Resource"] = statement["Resource"][0]
    before = copy.deepcopy((expected, actual))
    if reverse:
        expected, actual = actual, expected
    assert bucket_policy_equivalent(expected, actual)
    assert (expected, actual) == (before[::-1] if reverse else before)
    assert bucket_policy_equivalent(expected, json.dumps(actual))


@pytest.mark.parametrize(
    "field,value",
    [
        ("Resource", "arn:aws:s3:::different-bucket/*"),
        ("Resource", ["arn:aws:s3:::different-bucket/*"]),
        ("Resource", []),
        ("Resource", ["*"]),
        ("Principal", {"AWS": "arn:aws:iam::123456789012:root"}),
        ("Principal", ["*"]),
        ("Action", "s3:GetObject"),
        ("Action", ["s3:PutObject"]),
        ("Effect", "Allow"),
        ("Condition", {}),
        ("Condition", {"StringEquals": {"aws:SecureTransport": "true"}}),
        ("Sid", "DifferentStatement"),
        ("NotResource", "*"),
    ],
)
def test_substantive_statement_changes_are_rejected(settings, field, value):
    expected = bucket_policy(settings)
    actual = copy.deepcopy(expected)
    actual["Statement"][1][field] = value
    assert not bucket_policy_equivalent(expected, actual)


@pytest.mark.parametrize("change", ["extra", "duplicate", "reorder", "missing"])
def test_resource_set_and_order_remain_strict(settings, change):
    expected = bucket_policy(settings)
    actual = copy.deepcopy(expected)
    resources = actual["Statement"][0]["Resource"]
    if change == "extra":
        resources.append("arn:aws:s3:::other")
    elif change == "duplicate":
        actual["Statement"][1]["Resource"] *= 2
    elif change == "reorder":
        resources.reverse()
    else:
        actual["Statement"][1].pop("Resource")
    assert not bucket_policy_equivalent(expected, actual)


@pytest.mark.parametrize("change", ["version", "extra", "order", "missing", "type"])
def test_document_structure_remains_strict(settings, change):
    expected = bucket_policy(settings)
    actual = copy.deepcopy(expected)
    if change == "version":
        actual["Version"] = "2008-10-17"
    elif change == "extra":
        actual["Id"] = "unexpected"
    elif change == "order":
        actual["Statement"].reverse()
    elif change == "missing":
        actual["Statement"].pop()
    else:
        actual["Statement"] = {}
    assert not bucket_policy_equivalent(expected, actual)


def test_wildcard_representation_is_not_normalized():
    expected = {"Statement": [{"Resource": "*"}]}
    assert not bucket_policy_equivalent(expected, {"Statement": [{"Resource": ["*"]}]})


def test_foundation_accepts_representation_but_hashes_actual_policy(s3, settings):
    s3.policy["Statement"][1]["Resource"] = s3.policy["Statement"][1]["Resource"][0]
    actual_hash = digest(canonical(s3.policy))
    assert actual_hash != digest(canonical(bucket_policy(settings)))
    assert verify_bucket_security(s3, settings) == actual_hash
    assert not s3.writes and not s3.deletes
    s3.policy["Statement"][1]["Condition"] = {}
    with pytest.raises(LabError, match="bucket_tls_or_encryption_policy_incompatible"):
        verify_bucket_security(s3, settings)


def test_nested_condition_resource_is_not_normalized(settings):
    expected = bucket_policy(settings)
    expected["Statement"][1]["Condition"]["StringEquals"] = {"Resource": ["arn:test"]}
    actual = copy.deepcopy(expected)
    actual["Statement"][1]["Condition"]["StringEquals"]["Resource"] = "arn:test"
    assert not bucket_policy_equivalent(expected, actual)
