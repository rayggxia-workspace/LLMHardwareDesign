"""Archive only explicitly allowed Issue70 evidence; never read model weights.

ZIP byte-integrity verification is not numerical/model/experiment acceptance.
The original FAIL/PARTIAL/status fields and every source byte are preserved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import zipfile

RESULT_DIRS = {"capture-granite03", "capture-falcon03", "numeric-granite02", "diagnose-granite01"}
AUDITS = ("audit-granite01", "audit-falcon03", "audit-diagnose-granite01",
          "audit-transport-granite01", "audit-transport-falcon01")
TRANSPORTS = ("transport-granite01", "transport-falcon01")
RECEIPTS = ("download_receipt.json", "relay_download_receipt.json")
WEIGHT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf", ".onnx", ".h5", ".hdf5"}
BLOCK = 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_name(value):
    require(isinstance(value, str) and "\\" not in value, "noncanonical member name")
    p = PurePosixPath(value)
    require(not p.is_absolute() and all(z not in ("", ".", "..") for z in p.parts), "member path escape")
    require(str(p) == value and ":" not in value, "noncanonical member path")
    return value


def inspect_path(root, path, *, directory=False):
    path = Path(path)
    require(path.is_relative_to(root), "path outside input root")
    current = path
    while current != root:
        require(not current.is_symlink(), "symlink rejected: " + str(current))
        current = current.parent
    require(path.resolve(strict=True).is_relative_to(root), "resolved path escape")
    mode = path.lstat().st_mode
    require(stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode), "nonregular input: " + str(path))
    if not directory:
        require(path.suffix.lower() not in WEIGHT_SUFFIXES, "weight file rejected: " + str(path))
        require(path.name not in (".env", "id_rsa", "id_ed25519") and path.suffix.lower() not in (".pem", ".key"),
                "credential file rejected")
    return path


def check_source_zip(path):
    """Inspect source capsule directory only, without opening any embedded body."""
    with zipfile.ZipFile(path) as z:
        seen = set()
        for item in z.infolist():
            name = item.filename.rstrip("/")
            relative_name(name)
            require(name not in seen, "duplicate source capsule member")
            seen.add(name)
            require(PurePosixPath(name).suffix.lower() not in WEIGHT_SUFFIXES, "weight inside source capsule")
            require(not stat.S_ISLNK(item.external_attr >> 16), "source capsule symlink")


def walk(root, directory):
    inspect_path(root, directory, directory=True)
    files = []
    for parent, dirs, names in os.walk(directory, followlinks=False):
        dirs.sort()
        for name in dirs:
            inspect_path(root, Path(parent) / name, directory=True)
        for name in sorted(names):
            path = inspect_path(root, Path(parent) / name)
            if path.suffix.lower() == ".zip" and path.is_relative_to(directory) and directory.name.startswith("phase"):
                check_source_zip(path)
            files.append(path)
    return files


def enumerate_inputs(root, out):
    files, missing = {}, []
    allowed_dirs = []
    for path in sorted(root.iterdir()):
        if path == out:
            continue
        name = path.name
        allowed = (name in RESULT_DIRS or fnmatch.fnmatchcase(name, "audit-*")
                   or fnmatch.fnmatchcase(name, "transport-*") or re.fullmatch(r"phase(?:[1-9]|10)", name))
        if name.endswith(".log"):
            member = inspect_path(root, path)
            files[name] = member
        elif allowed:
            allowed_dirs.append(name)
            for member in walk(root, path):
                files[member.relative_to(root).as_posix()] = member
    for name in sorted(RESULT_DIRS):
        if name not in allowed_dirs:
            missing.append(name)
    for model in ("granite", "falcon"):
        present = []
        for name in RECEIPTS:
            path = root / "models-relay" / model / name
            if path.exists() or path.is_symlink():
                inspect_path(root, path)
                files[path.relative_to(root).as_posix()] = path
                present.append(name)
        require(present, "missing allowed model download receipt: " + model)
    return files, allowed_dirs, missing


def selected_names(root, files):
    selected = {"numeric-granite02/" + n for n in ("witnesses.npz", "witnesses.json", "metrics.json", "manifest.json")}
    selected.add("capture-granite03/manifest.json")
    selected.update("capture-falcon03/" + n for n in ("projection.npz", "report.json", "manifest.json", "config.json"))
    selected.update(name + "/audit.json" for name in AUDITS)
    calendars = 0
    for name in TRANSPORTS:
        manifest = read_json(root / name / "manifest.json")
        require(isinstance(manifest.get("artifacts"), list), "transport manifest artifacts list required")
        selected.update(name + "/" + n for n in ("metrics.json", "manifest.json"))
        for row in manifest["artifacts"]:
            if row.get("kind") != "complete_copy_calendar":
                continue
            relative = relative_name(row["path"])
            key = name + "/" + relative
            require(key in files, "missing selected calendar")
            actual_sha, actual_bytes = sha(files[key])
            require(actual_sha == row["sha256"] and actual_bytes == row["bytes"], "calendar source manifest SHA mismatch")
            selected.add(key)
            calendars += 1
    require(calendars == 24, "expected exactly24 final01 transport calendars")
    require(selected.issubset(files), "required selected evidence absent: " + repr(sorted(selected - files.keys())))
    return sorted(selected)


def source_record(root, relative, path):
    relative_name(relative)
    digest, size = sha(inspect_path(root, path))
    st = path.stat()
    return {"path": relative, "bytes": size, "sha256": digest, "mtime_ns": st.st_mtime_ns}


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def make_archive(root, archive, index_name, records, contents_bytes, paths, prefix):
    require(not archive.exists(), "archive already exists")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for row in records:
            path = inspect_path(root, paths[row["path"]])
            info = zipfile.ZipInfo.from_file(path, prefix + "/" + row["path"])
            info.compress_type = zipfile.ZIP_STORED
            digest, size = hashlib.sha256(), 0
            # On the actual Linux server this also prevents a last-component symlink swap.
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
            with os.fdopen(fd, "rb") as source, z.open(info, "w", force_zip64=True) as dest:
                require(stat.S_ISREG(os.fstat(source.fileno()).st_mode), "opened input is not regular")
                for block in iter(lambda: source.read(BLOCK), b""):
                    digest.update(block)
                    size += len(block)
                    dest.write(block)
            require(digest.hexdigest() == row["sha256"] and size == row["bytes"], "source changed while archiving")
        z.writestr(prefix + "/" + index_name, contents_bytes, compress_type=zipfile.ZIP_STORED)
    expected = {prefix + "/" + row["path"]: row for row in records}
    expected[prefix + "/" + index_name] = {"bytes": len(contents_bytes), "sha256": hashlib.sha256(contents_bytes).hexdigest()}
    with zipfile.ZipFile(archive) as z:
        require(len(z.infolist()) == len(expected) and set(z.namelist()) == set(expected), "archive member set mismatch")
        for item in z.infolist():
            relative_name(item.filename)
            require(item.compress_type == zipfile.ZIP_STORED, "unexpected archive compression")
            row, digest, size = expected[item.filename], hashlib.sha256(), 0
            with z.open(item) as stream:
                for block in iter(lambda: stream.read(BLOCK), b""):
                    digest.update(block)
                    size += len(block)
            require(size == row["bytes"] and digest.hexdigest() == row["sha256"], "archive readback SHA mismatch")
    digest, size = sha(archive)
    return {"path": str(archive), "bytes": size, "sha256": digest, "members_verified": len(expected),
            "index_sha256": hashlib.sha256(contents_bytes).hexdigest(), "verification": "every stored member streamed and SHA-256 verified"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    args = p.parse_args()
    require(not args.root.is_symlink(), "symlink root rejected")
    root = args.root.resolve(strict=True)
    require(root.is_dir(), "input root is not a directory")
    require(not args.out.exists() and not args.out.is_symlink(), "output already exists")
    out = args.out.absolute()
    require(out.parent.resolve(strict=True).is_relative_to(root), "output must stay under Issue70 root")
    out = out.parent.resolve(strict=True) / out.name
    require(out != root and out.name not in RESULT_DIRS and not out.name.startswith(("audit-", "transport-", "phase")), "output overlaps input scope")
    binding_path = inspect_path(root, args.binding.absolute())
    binding = read_json(binding_path)
    require(re.fullmatch(r"[0-9a-f]{40}", binding.get("commit", "")), "binding commit required")
    source_path = inspect_path(root, Path(__file__).absolute())
    source_sha, _ = sha(source_path)
    require(binding.get("collect_sha256") == source_sha, "collector source binding mismatch")
    paths, directories, missing = enumerate_inputs(root, out)
    selection = selected_names(root, paths)
    # Collector/binding are already under phase10 when staged. Also give stable
    # explicit names so their provenance remains findable in future phase layouts.
    paths["_collector/collect.py"] = source_path
    paths["_collector/binding.json"] = binding_path
    records = [source_record(root, name, path) for name, path in sorted(paths.items())]
    now = datetime.now(timezone.utc).isoformat()
    context = {"schema": "issue70-byte-delivery-v1", "timestamp_utc": now, "input_root": str(root),
               "archive_rootname": root.name, "source": binding, "collector_sha256": source_sha,
               "host": socket.gethostname(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
               "qualification": "Archive-byte verification only. Original statuses including FAIL/PARTIAL remain unchanged. No model/numerical acceptance claim.",
               "snapshot_note": "Input bytes are snapshotted and checked during archive creation; the collector's own stdout log may gain its final receipt after this snapshot."}
    all_contents = {**context, "scope": "full explicitly allowlisted evidence", "allowed_directories_present": directories,
                    "missing_named_result_directories": missing, "files": records,
                    "file_count": len(records), "total_file_bytes": sum(r["bytes"] for r in records)}
    by_name = {r["path"]: r for r in records}
    selected_records = [by_name[name] for name in selection]
    small_contents = {**context, "scope": "partial portable selection; original manifests may refer to large artifacts available only in full archive",
                      "transport_calendars": 24, "final_audits": list(AUDITS), "files": selected_records,
                      "file_count": len(selected_records), "total_file_bytes": sum(r["bytes"] for r in selected_records),
                      "excluded_large_falcon_arrays": ["capture.npz", "numeric.npz"],
                      "qualification": context["qualification"] + " Selected package alone is not a full-model/full-result replay package."}
    out.mkdir(mode=0o700, exist_ok=False)
    full_bytes, small_bytes = json_bytes(all_contents), json_bytes(small_contents)
    write_new(out / "contents.json", full_bytes)
    write_new(out / "selected-contents.json", small_bytes)
    full = make_archive(root, out / "full-results.zip", "contents.json", records, full_bytes, paths, root.name)
    small = make_archive(root, out / "selected.zip", "selected-contents.json", selected_records, small_bytes, paths, root.name)
    receipt = {**context, "status": "ARCHIVE_BYTES_VERIFIED_ONLY", "full": full, "selected": small,
               "file_count": len(records), "selected_file_count": len(selected_records),
               "model_weight_files_read": False, "complete_results_may_contain_original_failures": True}
    write_new(out / "receipt.json", json_bytes(receipt))
    print(json.dumps({"status": receipt["status"], "out": str(out), "full_bytes": full["bytes"],
                      "full_sha256": full["sha256"], "selected_bytes": small["bytes"], "selected_sha256": small["sha256"]}), flush=True)


if __name__ == "__main__":
    main()
