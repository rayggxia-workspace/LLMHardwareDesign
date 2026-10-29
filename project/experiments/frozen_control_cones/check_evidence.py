"""Verify published export bytes and, optionally, server-only original evidence."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check(manifest, fixture_root, archive_root=None):
    data = json.loads(Path(manifest).read_text())
    checked = []
    entries = [(Path(fixture_root), x) for x in data["published_fixtures"]]
    if archive_root:
        entries += [(Path(archive_root), x) for x in data["server_artifacts"]]
    for root, record in entries:
        target = (root / record["path"]).resolve()
        if not target.is_relative_to(root.resolve()):
            raise ValueError("Evidence path escapes root: "+record["path"])
        raw = target.read_bytes()
        if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError("Evidence digest mismatch: "+record["path"])
        if archive_root and root == Path(fixture_root):
            src = Path(archive_root) / record["archive_path"]
            if src.read_bytes() != raw:
                raise ValueError("Published export differs from archive: "+record["path"])
        checked.append(record["path"])
    return {"passed": True, "files_verified": len(checked),
            "server_evidence_verified": bool(archive_root),
            "native_EDA_rerun": False, "new_SAT_run": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-root")
    p.add_argument("--manifest", default=str(HERE/"evidence.json"))
    a = p.parse_args()
    print(json.dumps(check(a.manifest, HERE, a.archive_root)))


if __name__ == "__main__":
    main()
