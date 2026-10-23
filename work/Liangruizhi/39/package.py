"""Deterministic local record packaging; no network or credentials."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
TEMP = Path("D:/Projects/Codex/kvscale-20261023")
RESULT = ROOT / "project/experiments/kv_scale/results/issue-39-run01"
RESULT.mkdir(parents=True, exist_ok=True)
archive = RESULT / "evidence.zip"
members = {"run01/"+p.name: p for p in (TEMP/"run01").iterdir() if p.is_file()}
members["run02/manifest.json"] = TEMP/"run02/manifest.json"
for name in ("management", "tests", "whitespace", "input-audit", "replay-audit"):
    members["checks/"+name+".log"] = TEMP/(name+".log")
digest = lambda raw: hashlib.sha256(raw).hexdigest()
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, path in sorted(members.items()):
        info = zipfile.ZipInfo(name, (2026, 10, 23, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, path.read_bytes())
index = {"schema": "issue39-evidence/1", "source_commit": "a83e624a10ecc3f012eff2f2f770c9f9842c3a76",
    "archive": {"path": archive.relative_to(ROOT).as_posix(), "bytes": archive.stat().st_size,
                "sha256": digest(archive.read_bytes())},
    "members": {name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
                for name, p in sorted(members.items())}}
(RESULT / "index.json").write_text(json.dumps(index, indent=2)+"\n", encoding="utf-8", newline="\n")
print(json.dumps({"archive": index["archive"], "members": len(members)}))
