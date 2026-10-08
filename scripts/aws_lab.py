"""PowerShell-friendly lab runner. Only prepare/validate are authorized in RP-12A."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cloud.aws.auth import authenticated_session, require_selection  # noqa: E402
from cloud.aws.contracts import LabError  # noqa: E402
from cloud.aws.prepare import load_prepared, prepare  # noqa: E402
from cloud.aws.settings import Settings  # noqa: E402
from cloud.aws.validation import validate  # noqa: E402

OPERATIONS = (
    "prepare",
    "validate",
    "preflight",
    "plan",
    "deploy",
    "run-etl",
    "query-checks",
    "endpoint-check",
    "inventory",
    "teardown",
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=OPERATIONS)
    for name in (
        "profile",
        "account",
        "region",
        "environment",
        "confirm",
        "expires-on",
    ):
        parser.add_argument("--" + name)
    for name in (
        "authorize-live",
        "budget-reviewed",
        "service-access-reviewed",
        "enable-endpoint",
    ):
        parser.add_argument("--" + name, action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "prepare":
            result = prepare(ROOT)
            summary = {
                k: result[k]
                for k in (
                    "mode",
                    "run_id",
                    "input_bytes",
                    "spark_executed",
                    "aws_executed",
                )
            }
            summary["metric_reference"] = result["metric_reference"]
        elif args.operation == "validate":
            load_prepared(ROOT)
            summary = validate(ROOT)
        else:
            require_selection(args)
            prepared = load_prepared(ROOT)
            settings = Settings(
                args.account, args.region, args.environment, prepared["run_id"]
            )
            # Process-local optional SDK path. The normal app never imports it.
            sys.path.insert(0, str(ROOT / "artifacts/rp12/sdk"))
            session = authenticated_session(args.profile, settings)
            if args.operation == "preflight":
                summary = {
                    "identity": "temporary assumed role in explicitly selected account/region",
                    "services_eligibility": "UNVERIFIED",
                    "cost_authorization": "NOT established by STS",
                    "budget_and_service_review_required_before_workloads": True,
                }
            else:
                from cloud.aws.operations import Operations

                operations = Operations(ROOT, settings, args, prepared, session)
                if args.operation not in {"plan", "deploy"}:
                    operations.initialize()
                summary = getattr(operations, args.operation.replace("-", "_"))()
        destination = ROOT / "artifacts/rp12" / f"{args.operation}_result.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    except (LabError, OSError, ValueError, KeyError, TypeError) as exc:
        message = (
            str(exc)
            if isinstance(exc, LabError)
            else "operation_failed_see_local_evidence"
        )
        print(json.dumps({"result": "FAIL", "reason": message}))
        return 1
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "result": "INTERRUPTED",
                    "cleanup": "Verify the exact lab inventory before retrying",
                }
            )
        )
        return 130
    except Exception:
        print(json.dumps({"result": "FAIL", "reason": "service_denied_or_unavailable"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
