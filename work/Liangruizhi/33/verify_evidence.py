"""Verify this task's bounded archive; optionally extract without overwriting edits."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--extract",action="store_true");a=p.parse_args()
    doc=json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))
    archive=ROOT/doc["archive"]["path"]
    assert archive.stat().st_size==doc["archive"]["bytes"] and sha(archive.read_bytes())==doc["archive"]["sha256"]
    wanted={x["path"]:x for x in doc["archive_files"]}
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(wanted)
        for name,item in wanted.items():
            pp=PurePosixPath(name)
            if pp.is_absolute() or ".." in pp.parts or "\\" in name or ":" in name:raise ValueError("unsafe member")
            target=(ROOT/name).resolve()
            if not target.is_relative_to(ROOT):raise ValueError("member escapes repository")
            data=z.read(name)
            assert len(data)==item["bytes"] and sha(data)==item["sha256"],name
            if a.extract:
                if target.exists() and sha(target.read_bytes())!=item["sha256"]:
                    raise ValueError("refusing to overwrite modified local file: "+name)
                target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():target.write_bytes(data)
    for item in doc["attachments"]:
        path=ROOT/item["path"]
        assert path.stat().st_size==item["bytes"] and sha(path.read_bytes())==item["sha256"],str(path)
    print(json.dumps({"archive_members":len(wanted),"attachments":len(doc["attachments"]),"all_sha256_passed":True,"extracted":a.extract}))


if __name__=="__main__":main()
