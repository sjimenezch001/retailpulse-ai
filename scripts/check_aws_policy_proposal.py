"""Check an already-rendered local proposal against cached official AWS references."""

import argparse
import fnmatch
import hashlib
import json
import re
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def check(directory, references):
    review = json.loads((directory / "review.json").read_text(encoding="utf-8"))
    metadata = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in references.glob("*.json")
        if path.stem in {"s3", "glue", "iam", "athena", "logs", "sts"}
    }
    counts = {"documents": 0, "allow_action_resource_pairs": 0, "condition_checks": 0}
    failures = []
    for name in review["sha256"]:
        document = json.loads((directory / name).read_text(encoding="utf-8"))
        counts["documents"] += 1
        if hashlib.sha256(canonical(document)).hexdigest() != review["sha256"][name]:
            failures.append(name + ": rendered review checksum mismatch")
        if name in {"glue-trust.json", "bucket-settings.json"}:
            continue
        if name != "bucket-policy.json" and len(canonical(document)) > 6144:
            failures.append(name + ": managed policy character limit")
        for statement in document["Statement"]:
            if statement["Effect"] != "Allow":
                continue
            actions = statement["Action"]
            resources = statement["Resource"]
            for action in actions:
                service, verb = action.split(":", 1)
                if "*" in action or service not in metadata:
                    failures.append(name + ": unsupported or wildcard Allow " + action)
                    continue
                ref = metadata[service]
                matches = [a for a in ref["Actions"] if a["Name"] == verb]
                if len(matches) != 1:
                    failures.append(name + ": unknown action " + action)
                    continue
                action_ref = matches[0]
                types = {r["Name"]: r for r in ref["Resources"]}
                resource_types = [
                    types[r["Name"]] for r in action_ref.get("Resources", [])
                ]
                patterns = [
                    re.sub(r"\$\{[^}]+\}", "*", arn)
                    for resource_type in resource_types
                    for arn in resource_type["ARNFormats"]
                ]
                keys = action_ref.get("ActionConditionKeys", []) + [
                    key
                    for resource_type in resource_types
                    for key in resource_type.get("ConditionKeys", [])
                ]
                keys = [re.sub(r"\$\{[^}]+\}", "*", key) for key in keys]
                for resource in resources:
                    counts["allow_action_resource_pairs"] += 1
                    valid = (
                        resource == "*"
                        and action == "logs:DescribeLogGroups"
                        and not resource_types
                    ) or any(
                        fnmatch.fnmatchcase(resource, pattern) for pattern in patterns
                    )
                    if not valid:
                        failures.append(
                            name
                            + ": unsupported action/resource "
                            + action
                            + " "
                            + resource
                        )
                for terms in statement.get("Condition", {}).values():
                    for key in terms:
                        counts["condition_checks"] += 1
                        if key not in {
                            "aws:PrincipalArn",
                            "aws:PrincipalAccount",
                            "aws:RequestedRegion",
                        } and not any(
                            fnmatch.fnmatchcase(key, pattern) for pattern in keys
                        ):
                            failures.append(
                                name + ": unsupported condition " + action + " " + key
                            )
    return {
        "mode": "offline",
        "aws_account_calls": 0,
        "counts": counts,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.directory, args.references)
    (args.directory / "static-validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["failures"]))


if __name__ == "__main__":
    main()
