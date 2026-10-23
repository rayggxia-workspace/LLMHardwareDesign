"""Hash-check delivered files and archive; optional safe extraction into a new D directory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser()
p.add_argument("--extract", type=Path)
a = p.parse_args()
digest = lambda raw: hashlib.sha256(raw).hexdigest()
index = json.loads((ROOT / "project/experiments/kv_scale/results/issue-39-run01/index.json").read_text())
archive = ROOT / index["archive"]["path"]
assert archive.stat().st_size == index["archive"]["bytes"]
assert digest(archive.read_bytes()) == index["archive"]["sha256"]
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist()) == len(set(z.namelist()))
    assert set(z.namelist()) == set(index["members"])
    for name, expected in index["members"].items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts and "\\" not in name
        raw = z.read(name)
        assert len(raw) == expected["bytes"] and digest(raw) == expected["sha256"]
        if a.extract:
            if a.extract.resolve().drive.lower() != "d:":
                raise ValueError("this user's extraction destination must be on D")
            target = a.extract / name
            if target.exists() and target.read_bytes() != raw:
                raise ValueError("refuse to overwrite different existing data")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
delivery = ROOT / "work/Liangruizhi/39/manifest.json"
file_checks = 0
if delivery.exists():
    for name, record in json.loads(delivery.read_text())["files"].items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == record["bytes"] and digest(raw) == record["sha256"], name
        file_checks += 1
print(json.dumps({"status": "PASS", "archive_members": len(index["members"]),
    "delivery_file_hashes": file_checks, "extracted": str(a.extract) if a.extract else None}))
