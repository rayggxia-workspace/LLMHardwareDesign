"""Verify a delivery archive and every member against the published index.

This is byte reception only. It does not rerun tensor math or accept hardware.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath


def digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(8 << 20), b""):
        value.update(block)
    return value.hexdigest()


def verify(index_path, archive_path):
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    archive_path = Path(archive_path)
    records = [r for r in index["archives"] if Path(r["path"]).name == archive_path.name]
    if len(records) != 1:
        raise ValueError("archive absent or ambiguous in index")
    record = records[0]
    with archive_path.open("rb") as stream:
        actual_hash = digest(stream)
    if archive_path.stat().st_size != record["bytes"] or actual_hash != record["sha256"]:
        raise ValueError("archive bytes/SHA mismatch")
    expected = {r["path"]: r for r in index["files"]}
    required = set(index["selected_paths"]) if archive_path.name == "selected.zip" else set(expected)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != required or len(names) != record["members"]:
            raise ValueError("archive members differ from index")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename:
                raise ValueError("unsafe archive member")
            with archive.open(item) as stream:
                member_hash = digest(stream)
            entry = expected[item.filename]
            if item.file_size != entry["bytes"] or member_hash != entry["sha256"]:
                raise ValueError("member bytes/SHA mismatch: " + item.filename)
    return {"schema": "issue72-byte-reception-v1", "status": "PASS_BYTE_RECEPTION",
            "archive": archive_path.name, "bytes": record["bytes"], "sha256": actual_hash,
            "members_checked": len(required), "source_commit": index["source_commit"],
            "limits": ["Byte reception only; see separately bound server mathematical receipts.",
                       "No application quality, native INT8 speed, RTL or PPA acceptance."]}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("refuse receipt overwrite")
    receipt = verify(args.index, args.archive)
    with args.out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], receipt["members_checked"])


if __name__ == "__main__":
    main()
