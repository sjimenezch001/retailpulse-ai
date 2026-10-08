"""Cross-platform, fail-fast development tasks; invoke with the project Python."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task",
        choices=[
            "setup",
            "lint",
            "typecheck",
            "test",
            "security",
            "secrets",
            "build",
            "demo",
            "verify",
            "docker",
        ],
    )
    task = parser.parse_args().task
    python = sys.executable
    (ROOT / "reports").mkdir(exist_ok=True)
    commands = {
        "lint": [python, "-m", "ruff", "check", "."],
        "typecheck": [python, "-m", "mypy"],
        "test": [
            python,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--cov",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=xml:reports/coverage.xml",
            "--cov-report=json:reports/coverage.json",
        ],
        "secrets": [python, "scripts/scan_secrets.py"],
        "build": [python, "-m", "build", "--no-isolation"],
        "demo": [
            python,
            "-m",
            "retailpulse",
            "demo",
            "--mode",
            "synthetic",
            "--provider",
            "deterministic",
        ],
        "docker": ["docker", "compose", "build"],
    }
    if task == "setup":
        run(python, "-m", "pip", "install", "-r", "requirements-dev.txt")
        run(
            python,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-build-isolation",
            "-e",
            ".",
        )
    elif task == "security":
        # --strict makes lookup errors fail. JSON contains package metadata only.
        run(python, "scripts/audit_dependencies.py")
        run(*commands["secrets"])
    elif task == "verify":
        for step in ("lint", "typecheck", "test"):
            run(*commands[step])
        run(python, "-m", "pip", "check")
        run("git", "diff", "--check")
    else:
        run(*commands[task])


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, OSError):
        sys.exit(1)
