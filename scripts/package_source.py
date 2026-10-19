"""Reproducible source ZIP with Windows line endings, no local build/private files."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bridge81 import __version__


def main():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    paths = sorted(part.decode("utf-8") for part in result.stdout.split(b"\0") if part)
    if not paths:
        raise SystemExit("Stage project files with git add before packaging.")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    target = output / ("Bridge81-%s-source.zip" % __version__)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in paths:
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise SystemExit("Only ordinary tracked files can be packaged: %s" % name)
            data = path.read_bytes()
            if name.endswith((".cmd", ".ps1")):
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            info = zipfile.ZipInfo("Bridge81/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / (target.name + ".sha256")).write_text("%s  %s\n" % (digest, target.name), encoding="ascii")
    print(target)
    print(digest)


if __name__ == "__main__":
    main()
