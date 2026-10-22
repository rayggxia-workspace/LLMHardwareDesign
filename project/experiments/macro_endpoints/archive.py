"""Lossless small archive of captured inputs and deterministic exported data."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile
from common import (clean_provenance, file_index, git, json_bytes, sha, utc_now,
                    verify_index, verify_provenance)
from verify import verify


def verify_figures(folder, run, archived=False):
    folder, run = Path(folder), Path(run)
    report = json.loads((folder / "report-manifest.json").read_bytes())
    if set(report["files"]) != {"signal-pin-centers.png", "signal-pin-centers.svg", "table.md"}:
        raise AssertionError("unexpected figure artifacts or reserved sidecar names")
    if archived:
        for name, info in report["files"].items():
            data = (folder / name).read_bytes()
            if len(data) != info["bytes"] or sha(data) != info["sha256"]:
                raise AssertionError("archived figure differs from report index")
    else:
        verify_index(folder, report["files"], "report-manifest.json")
    manifest_name = "run-manifest.json" if archived else "manifest.json"
    if report["input_export_manifest_sha256"] != sha((run / manifest_name).read_bytes()):
        raise AssertionError("figures belong to a different export")
    if report["plotter_source_sha256"] != sha(Path(__file__).with_name("report.py").read_bytes()):
        raise AssertionError("figure source does not match this plotter")
    verify_provenance(report["provenance"], require_current=True)


def verify_archive(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "archive-manifest.json").read_bytes())
    actual = {p.name for p in folder.iterdir() if p.is_file()}
    if actual != {*manifest["files"], "archive-manifest.json"}:
        raise AssertionError("unindexed archive artifact")
    for name, info in manifest["files"].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder):
            raise AssertionError("unsafe artifact path")
        data = path.read_bytes()
        if len(data) != info["bytes"] or sha(data) != info["sha256"]:
            raise AssertionError("archive artifact mismatch: " + name)
    with zipfile.ZipFile(folder / "evidence.zip") as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(set(archive.namelist())):
            raise AssertionError("invalid archive")
        if set(archive.namelist()) != set(manifest["zip_files"]):
            raise AssertionError("unindexed zip member")
        for name, info in manifest["zip_files"].items():
            parts = PurePosixPath(name)
            if parts.is_absolute() or ".." in parts.parts or parts.parts[0] not in ("inputs", "outputs"):
                raise AssertionError("unsafe zip member")
            data = archive.read(name)
            if len(data) != info["bytes"] or sha(data) != info["sha256"]:
                raise AssertionError("raw zip bytes changed: " + name)
        if sha(archive.read("inputs/capture.json")) != manifest["capture_manifest_sha256"]:
            raise AssertionError("capture manifest mismatch")
        if sha(archive.read("outputs/manifest.json")) != manifest["export_manifest_sha256"]:
            raise AssertionError("export manifest mismatch")
        capture = json.loads(archive.read("inputs/capture.json"))
        exported = json.loads(archive.read("outputs/manifest.json"))
        if (capture["provenance"]["source_commit"] != manifest["capture_source_commit"]
                or exported["provenance"]["source_commit"] != manifest["export_source_commit"]):
            raise AssertionError("archive source commit differs from inner provenance")
        for outer, inner in (("capture-manifest.json", "inputs/capture.json"),
                             ("run-manifest.json", "outputs/manifest.json"),
                             ("summary.json", "outputs/summary.json")):
            if (folder / outer).read_bytes() != archive.read(inner):
                raise AssertionError("archive sidecar differs from inner data: " + outer)
    verify_provenance(manifest["provenance"], require_current=True)
    verify_figures(folder, folder, archived=True)
    return {"status": "PASS", "zip_files": len(manifest["zip_files"]),
            "capture_source_commit": manifest["capture_source_commit"],
            "export_source_commit": manifest["export_source_commit"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path)
    p.add_argument("--run", type=Path)
    p.add_argument("--figures", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--verify", type=Path)
    a = p.parse_args()
    if a.verify:
        print(json.dumps(verify_archive(a.verify), indent=2))
        return
    if not a.snapshot or not a.run or not a.figures or not a.out or a.out.exists():
        raise SystemExit("Provide --snapshot --run --figures --out, with a NEW destination")
    provenance = clean_provenance(["archive.py", "common.py", "verify.py", "export.py", "lef_profile.py", "inputs.json"])
    checked = verify(a.snapshot, a.run, replay=True)
    verify_figures(a.figures, a.run)
    a.out.mkdir(parents=True)
    zip_index = {}
    with zipfile.ZipFile(a.out / "evidence.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for prefix, folder in (("inputs", a.snapshot), ("outputs", a.run)):
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    name = prefix + "/" + path.relative_to(folder).as_posix()
                    data = path.read_bytes()
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data, compresslevel=9)
                    zip_index[name] = {"bytes": len(data), "sha256": sha(data)}
    for path, name in ((a.snapshot / "capture.json", "capture-manifest.json"),
                       (a.run / "manifest.json", "run-manifest.json"),
                       (a.run / "summary.json", "summary.json")):
        shutil.copyfile(path, a.out / name)
    for path in sorted(a.figures.iterdir()):
        if path.is_file():
            shutil.copyfile(path, a.out / path.name)
    manifest = {"schema": 1, "packaged_utc": utc_now(),
                "capture_source_commit": checked["capture_source_commit"],
                "export_source_commit": checked["export_source_commit"],
                "capture_manifest_sha256": sha((a.snapshot / "capture.json").read_bytes()),
                "export_manifest_sha256": sha((a.run / "manifest.json").read_bytes()),
                "postprocessor_head": git("rev-parse", "HEAD"),
                "provenance": provenance,
                "packager_source_sha256": sha(Path(__file__).read_bytes()),
                "zip_files": zip_index, "files": file_index(a.out)}
    (a.out / "archive-manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps(verify_archive(a.out), indent=2))


if __name__ == "__main__":
    main()
