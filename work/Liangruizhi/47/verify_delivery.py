"""Verify the small Issue47 archive; optional extraction refuses unsafe paths/overwrite."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
import zipfile


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify(index_path,destination=None):
    index=json.loads(index_path.read_text(encoding="utf-8"))
    archive=index_path.parent/index["archive"]["file"]
    raw=archive.read_bytes()
    assert len(raw)==index["archive"]["bytes"] and sha(raw)==index["archive"]["sha256"]
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        assert len(names)==len(set(names)) and set(names)==set(index["members"])
        total=0;payload=[]
        for info in z.infolist():
            path=PurePosixPath(info.filename);mode=info.external_attr>>16
            assert not path.is_absolute() and ".." not in path.parts and "\\" not in info.filename
            assert not info.is_dir() and not stat.S_ISLNK(mode)
            data=z.read(info.filename);expected=index["members"][info.filename]
            assert len(data)==expected["bytes"] and sha(data)==expected["sha256"],info.filename
            total+=len(data);payload.append((path,data))
        if destination:
            if destination.exists():raise ValueError("refuse overwrite")
            base=destination.resolve()
            for path,_ in payload:(base/str(path)).resolve().relative_to(base)
            destination.mkdir(parents=True)
            for path,data in payload:
                target=destination/str(path);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return {"status":"PASS","archive_sha256":sha(raw),"files_checked":len(names),"uncompressed_bytes":total}


def main():
    p=argparse.ArgumentParser();p.add_argument("index",type=Path);p.add_argument("--extract",type=Path)
    a=p.parse_args();print(json.dumps(verify(a.index,a.extract)))

if __name__=="__main__":main()
