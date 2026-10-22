"""Postprocessing packager: keep all original evidence bytes in a small ZIP.

Added after the experiment source snapshot; its hash is recorded separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import zlib


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(folder):
    manifest = json.loads((folder/"archive-manifest.json").read_text(encoding="utf-8"))
    for name, info in manifest["files"].items():
        path = (folder/name).resolve()
        assert path.is_relative_to(folder.resolve())
        assert path.stat().st_size == info["bytes"] and sha(path) == info["sha256"], name
    with zipfile.ZipFile(folder/"raw-evidence.zip") as archive:
        assert archive.testzip() is None
        raw_manifest = json.loads(archive.read("manifest.json"))
        assert hashlib.sha256(archive.read("manifest.json")).hexdigest() == manifest["original_manifest_sha256"]
        assert set(archive.namelist()) == {*raw_manifest["files"], "manifest.json"}
        for name, info in raw_manifest["files"].items():
            data = archive.read(name)
            assert len(data) == info["bytes"] and hashlib.sha256(data).hexdigest() == info["sha256"], name
        assert raw_manifest["source_commit"] == manifest["experiment_source_commit"]
    return {"status": "PASS", "archive_files": len(manifest["files"]),
            "raw_files": len(raw_manifest["files"])+1, "source_commit": raw_manifest["source_commit"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path)
    p.add_argument("--figures", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--verify", type=Path)
    a = p.parse_args()
    if a.verify:
        print(json.dumps(verify(a.verify), indent=2))
        return
    if not a.run or not a.figures or not a.out or a.out.exists():
        raise SystemExit("Provide --run --figures --out with a NEW output directory")
    a.out.mkdir(parents=True)
    raw_manifest = json.loads((a.run/"manifest.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(a.out/"raw-evidence.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for f in sorted(a.run.rglob("*")):
            if f.is_file():
                name = f.relative_to(a.run).as_posix()
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, f.read_bytes(), compresslevel=9)
    shutil.copyfile(a.run/"summary.json", a.out/"summary.json")
    shutil.copyfile(a.run/"manifest.json", a.out/"run-manifest.json")
    for name in ["routing-summary.csv", "routing-success.svg", "routing-success.png", "table.md", "report-manifest.json"]:
        shutil.copyfile(a.figures/name, a.out/name)
    receipt = {"experiment_source_commit": raw_manifest["source_commit"],
               "original_manifest_sha256": sha(a.run/"manifest.json"),
               "packager_source_sha256": sha(Path(__file__)), "zlib": zlib.ZLIB_VERSION,
               "note": "Postprocessing only; do not backdate packager as experiment source.",
               "files": {f.name: {"bytes": f.stat().st_size, "sha256": sha(f)} for f in sorted(a.out.iterdir())}}
    (a.out/"archive-manifest.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(verify(a.out), indent=2))


if __name__ == "__main__":
    main()
