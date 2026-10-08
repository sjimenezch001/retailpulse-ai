"""Exercise Git's real checkout conversion, including the original Windows failure."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import duckdb
import pytest

from retailpulse.api import source

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path("src/retailpulse/api/synthetic")


@pytest.mark.parametrize("windows", [False, True], ids=["linux-lf", "windows-crlf"])
@pytest.mark.parametrize("protected", [False, True], ids=["original", "attributes"])
def test_snapshot_through_git_checkout(tmp_path, monkeypatch, windows, protected):
    repository = tmp_path / "repository"
    repository.mkdir()
    # Keep developer/system attributes and config out of this isolated experiment.
    env = {
        **os.environ,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
    }

    def git(*args):
        return subprocess.check_output(
            ["git", "-c", f"core.attributesFile={os.devnull}", *args],
            cwd=repository,
            env=env,
            stderr=subprocess.STDOUT,
        )

    git("init", "--quiet")
    git("config", "core.autocrlf", "false")
    git("config", "core.eol", "lf")
    original = ROOT / PACKAGE
    manifest = json.loads((original / "manifest.json").read_text(encoding="utf-8"))
    files = ["manifest.json", *(f"{name}.csv" for name in manifest["tables"])]
    canonical = {name: (original / name).read_bytes() for name in files}
    for name in manifest["tables"]:
        assert hashlib.sha256(canonical[f"{name}.csv"]).hexdigest() == manifest["sha256"][name]
    target = repository / PACKAGE
    target.mkdir(parents=True)
    for name, content in canonical.items():
        (target / name).write_bytes(content)
    (repository / "control.txt").write_bytes(b"one\ntwo\n")
    if protected:
        (repository / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    git("add", ".")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    git(
        "-c", f"core.autocrlf={'true' if windows else 'false'}",
        "-c", f"core.eol={'crlf' if windows else 'lf'}",
        "checkout-index", "--all", f"--prefix={checkout.as_posix()}/",
    )
    # This control proves Git really applied the requested platform's conversion.
    assert (checkout / "control.txt").read_bytes() == (
        b"one\r\ntwo\r\n" if windows else b"one\ntwo\n"
    )
    monkeypatch.setattr(source, "SYNTHETIC", checkout / PACKAGE)
    output = tmp_path / "database"
    if windows and not protected:
        for name in manifest["tables"]:
            content = (source.SYNTHETIC / f"{name}.csv").read_bytes()
            assert b"\r\n" in content
            assert hashlib.sha256(content).hexdigest() != manifest["sha256"][name]
        with pytest.raises(ValueError, match="failed integrity validation"):
            source.portable_database(output)
        assert not output.exists()
        return

    for name, content in canonical.items():
        assert (source.SYNTHETIC / name).read_bytes() == content
    digest = hashlib.sha256(canonical["manifest.json"])
    for name in manifest["tables"]:
        digest.update(canonical[f"{name}.csv"])
    database = source.portable_database(output)
    assert database.name == f"synthetic-{digest.hexdigest()[:16]}.duckdb"
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            "SELECT sum(units) FROM mart_sales_daily WHERE store_id = 'SYN_A'"
        ).fetchone() == (378,)
