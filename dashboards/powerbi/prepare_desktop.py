"""Copy the portable project into ignored local storage and configure its CSV path."""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def prepare():
    data = ROOT / "artifacts/powerbi/data"
    if not (data / "manifest.json").is_file():
        raise SystemExit("Run python -m retailpulse export-bi before preparing Desktop.")
    target = ROOT / "artifacts/powerbi/project"
    target.mkdir(parents=True, exist_ok=True)
    # Only reusable definitions are copied. Existing Desktop caches are preserved.
    for name in ("RetailPulse.Report", "RetailPulse.SemanticModel"):
        shutil.copytree(HERE / name, target / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".pbi"))
    shutil.copy2(HERE / "RetailPulse.pbip", target / "RetailPulse.pbip")
    parameter = target / "RetailPulse.SemanticModel/definition/expressions.tmdl"
    source = parameter.read_text(encoding="utf-8-sig")
    configured = source.replace('expression DataFolder = ""', 'expression DataFolder = "' + data.as_posix().replace('"', '""') + '"')
    if configured == source:
        raise SystemExit("The portable DataFolder parameter was not found; no model overwritten.")
    parameter.write_text(configured, encoding="utf-8")
    (target.parent / "local-project.json").write_text(json.dumps({"project": str(target / "RetailPulse.pbip"), "data": str(data)}, indent=2) + "\n", encoding="utf-8")
    print(target / "RetailPulse.pbip")


if __name__ == "__main__":
    prepare()
