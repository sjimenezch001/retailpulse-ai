"""Run local checks with the invoking environment; no dataset downloads."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for arguments in (("-m", "ruff", "check", "."), ("-m", "pytest"), ("-m", "pip", "check")):
    subprocess.run([sys.executable, *arguments], cwd=root, check=True)
subprocess.run(["git", "diff", "--check"], cwd=root, check=True)
