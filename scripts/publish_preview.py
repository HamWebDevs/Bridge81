"""CI-only release publisher. Never overwrites an existing version or artifact."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bridge81 import __version__
from bridge81.pe import inspect_pe


def main():
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    commit = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SystemExit("Run this publisher only in GitHub Actions with an explicit repository and commit.")
    if not re.fullmatch(r"\d+\.\d+\.\d+", __version__):
        raise SystemExit("Release version must be major.minor.patch.")
    source = ROOT / "dist"
    wheels = list(source.glob("*.whl"))
    sdists = list(source.glob("*.tar.gz"))
    source_zip = source / ("Bridge81-%s-source.zip" % __version__)
    desktop = ROOT / "desktop" / "Bridge81"
    if len(wheels) != 1 or len(sdists) != 1 or not source_zip.is_file():
        raise SystemExit("Exactly one wheel, sdist and source ZIP are required.")
    pe = inspect_pe(desktop / "Bridge81.exe")
    if pe.architecture != "x64":
        raise SystemExit("Desktop build is not the expected x64 executable.")
    desktop_zip = source / ("Bridge81-%s-windows-x64-preview.zip" % __version__)
    with zipfile.ZipFile(desktop_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(desktop.rglob("*")):
            if path.is_symlink():
                raise SystemExit("Unexpected symlink in desktop artifact.")
            if path.is_file():
                archive.write(path, path.relative_to(desktop.parent).as_posix())
    assets = sorted([wheels[0], sdists[0], source_zip, desktop_zip], key=lambda p: p.name)
    sums = source / "SHA256SUMS"
    sums.write_text("".join("%s  %s\n" % (hashlib.sha256(p.read_bytes()).hexdigest(), p.name) for p in assets), encoding="ascii")
    subprocess.run(["gh", "release", "create", "v" + __version__, "--repo", repository, "--target", commit,
                    "--title", "Bridge81 %s preview" % __version__, "--prerelease",
                    "--notes-file", str(ROOT / "docs/release-notes.md"), *map(str, assets), str(sums)], check=True)


if __name__ == "__main__":
    main()
