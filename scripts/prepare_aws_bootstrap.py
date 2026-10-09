"""Write a local review bundle; never authenticate or execute owner bootstrap."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cloud.aws.policies import write_bundle  # noqa: E402
from cloud.aws.prepare import load_prepared  # noqa: E402
from cloud.aws.settings import Settings  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("account", "region", "environment"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    prepared = load_prepared(ROOT)
    settings = Settings(
        args.account, args.region, args.environment, prepared["run_id"]
    )
    target = ROOT / "artifacts/rp12c" / settings.run_id / "owner-review"
    result = write_bundle(settings, target)
    print(
        json.dumps(
            {
                "status": result["status"],
                "run_id": settings.run_id,
                "directory": str(target),
                "aws_calls": 0,
                "policies_installed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
