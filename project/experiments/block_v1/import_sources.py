"""Import the pinned scientific sources without touching upstream workspaces."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def import_sources(archive, manifest_path, root, receipt):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_bytes = archive.read_bytes()
    expected = manifest["archive"]
    if len(archive_bytes) != expected["bytes"] or digest(archive_bytes) != expected["sha256"]:
        raise ValueError("archive does not match the externally pinned identity")
    pending = []
    records = []
    root = root.resolve()
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)) or len(names) != expected["members"]:
            raise ValueError("duplicate archive members or wrong member count")
        for info in zf.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise ValueError("unsafe archive member")
        for path, identity in manifest["sources"].items():
            relative = PurePosixPath(path)
            if relative.is_absolute() or ".." in relative.parts or not path.startswith("project/"):
                raise ValueError("source destination outside project")
            data = zf.read(identity["archive_path"])
            if digest(data) != identity["scientific_sha256"]:
                raise ValueError("scientific source SHA mismatch: " + path)
            target = root.joinpath(*relative.parts)
            if root not in target.resolve().parents:
                raise ValueError("destination escapes checkout")
            if target.exists() and target.read_bytes() != data:
                raise ValueError("refusing to overwrite different existing source: " + path)
            git_blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            records.append({"path": path, "bytes": len(data), "scientific_sha256": digest(data),
                            "git_blob": git_blob,
                            "matches_published_blob": git_blob == identity["published_git_blob"]})
            pending.append((target, data))
    # Validate the whole import before any source write.
    for target, data in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
    result = {"schema": "block-v1-source-import/1", "reference_commit": manifest["reference_commit"],
              "scientific_source_commit": manifest["scientific_source_commit"],
              "archive_sha256": digest(archive_bytes), "sources": records,
              "all_scientific_sources_verified": True,
              "all_published_blobs_match": all(r["matches_published_blob"] for r in records)}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(records), "scientific_verified": True,
                      "all_published_blobs_match": result["all_published_blobs_match"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    import_sources(args.archive, args.manifest, args.root, args.receipt)
