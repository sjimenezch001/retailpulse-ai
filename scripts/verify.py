"""Run local checks with the invoking environment; no dataset downloads."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "scripts/tasks.py", "verify"], cwd=root, check=True)
