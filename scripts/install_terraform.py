"""Install the pinned official Terraform binary locally after checksum verification."""

import hashlib
import io
import platform
import urllib.request
import zipfile
from pathlib import Path

VERSION = "1.15.9"
ROOT = Path(__file__).resolve().parents[1]


def main():
    systems = {"Windows": "windows", "Linux": "linux", "Darwin": "darwin"}
    machines = {
        "AMD64": "amd64",
        "x86_64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    system, machine = systems[platform.system()], machines[platform.machine()]
    filename = f"terraform_{VERSION}_{system}_{machine}.zip"
    base = f"https://releases.hashicorp.com/terraform/{VERSION}/"
    with urllib.request.urlopen(
        base + f"terraform_{VERSION}_SHA256SUMS", timeout=60
    ) as response:
        lines = response.read().decode().splitlines()
    expected = next(line.split()[0] for line in lines if line.split()[-1] == filename)
    with urllib.request.urlopen(base + filename, timeout=120) as response:
        payload = response.read(100 * 1024 * 1024 + 1)
    if (
        len(payload) > 100 * 1024 * 1024
        or hashlib.sha256(payload).hexdigest() != expected
    ):
        raise ValueError("Terraform download failed checksum/size validation")
    binary = "terraform.exe" if system == "windows" else "terraform"
    target = ROOT / "artifacts/rp12/tools" / binary
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        target.write_bytes(archive.read(binary))
    target.chmod(0o755)
    print(
        f"Verified HashiCorp SHA-256; installed Terraform {VERSION}: {target.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
