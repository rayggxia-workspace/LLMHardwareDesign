"""Hash new experiment outputs on compute resources, including partial failed attempts."""
import hashlib
from pathlib import Path

paths = []
for base in (Path("flow/results"), Path("flow/reports"), Path("flow/logs")):
    if base.exists():
        paths.extend(p for p in base.rglob("*") if p.is_file())
paths.extend(p for p in Path(".").iterdir() if p.is_file() and p.suffix in (".json", ".log", ".sdc", ".mk", ".sv", ".ys"))
with Path("output-files.sha256").open("w") as out:
    for path in sorted(paths):
        digest = hashlib.sha256()
        with path.open("rb") as src:
            for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        out.write(digest.hexdigest() + "  " + str(path) + "\n")
