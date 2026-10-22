"""Package original outputs after clean-source runs; never re-label development."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8", newline="\n")


base, dest = map(Path, sys.argv[1:3])
dest.mkdir(parents=True, exist_ok=False)
expected = "6ffb9417f0f01f614b733ce6c3ca9837906b3203"
replay = {}
members = {}
for family, filenames in (("run", ["cases.json", "static-choices.json", "trace-binding.json", "witnesses.json.gz", "summary.json"]),
                          ("capture", ["attention-stages.npz", "inputs.json", "numeric-results.json"])):
    a, b = base/(family+"-01"), base/(family+"-02")
    first, second = [json.loads((p/"manifest.json").read_text()) for p in (a, b)]
    assert first["source_commit"] == second["source_commit"] == expected
    assert not first.get("development", first.get("development_run"))
    assert not second.get("development", second.get("development_run"))
    if family == "capture":
        assert first["status"] == second["status"] == "PASS"
        assert all(m["source_clean_at_end"] and m["source_unchanged_at_end"] and m["model_files_unchanged_at_end"] for m in (first, second))
    replay[family] = {name: dict(first_sha256=digest(a/name), second_sha256=digest(b/name),
                                byte_identical=(a/name).read_bytes() == (b/name).read_bytes()) for name in filenames}
    assert all(v["byte_identical"] for v in replay[family].values())
    for p in sorted(a.iterdir()):
        if p.is_file():
            members[family+"/"+p.name] = p
    members[family+"/replay-manifest.json"] = b/"manifest.json"
zip_path = dest/"evidence.zip"
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, p in sorted(members.items()):
        info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, p.read_bytes())
with zipfile.ZipFile(zip_path) as z:
    assert set(z.namelist()) == set(members)
    assert all(z.read(name) == p.read_bytes() for name, p in members.items())
save(dest/"archive-sha256.json", dict(source_commit=expected, archive=dict(bytes=zip_path.stat().st_size, sha256=digest(zip_path)),
                                    members={name:dict(bytes=p.stat().st_size, sha256=digest(p)) for name,p in sorted(members.items())}))
save(dest/"replay.json", replay)
save(dest/"summary.json", dict(resource=json.loads((base/"run-01/summary.json").read_text()),
                              capture={k:v for k,v in json.loads((base/"capture-01/numeric-results.json").read_text()).items()
                                       if k not in ("records", "stages")},
                              source_commit=expected, archive_sha256=digest(zip_path)))
print(json.dumps(dict(archive_bytes=zip_path.stat().st_size, archive_sha256=digest(zip_path), members=len(members),
                     replay_files=sum(map(len,replay.values())))))
