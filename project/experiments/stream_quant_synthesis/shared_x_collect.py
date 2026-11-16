"""Recover source and receipts from one exclusive run with bytewise SHA audit."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument("tag")
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
assert args.tag.isdigit()
root = "/public/home/yuzelu/project-circuit/issue250-shared-x-20261110-" + args.tag
payload = '''import base64,hashlib,io,json,tarfile
from pathlib import Path
r=Path(ROOT)
files={p.relative_to(r).as_posix():p.read_bytes() for p in sorted(r.rglob('*')) if p.is_file() and p.name not in ('candidate.exe','source.tar.gz')}
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as a:
 for n,d in files.items():
  m=tarfile.TarInfo(n);m.size=len(d);a.addfile(m,io.BytesIO(d))
raw=b.getvalue()
print(json.dumps(dict(root=str(r),archive_SHA256=hashlib.sha256(raw).hexdigest(),members_SHA256={n:hashlib.sha256(d).hexdigest() for n,d in files.items()},archive_base64=base64.b64encode(raw).decode())))
'''.replace("ROOT", repr(root))
result = json.loads(subprocess.check_output(["ssh", "-o", "BatchMode=yes", "yuzelu@10.129.166.172", "python3 -"], input=payload, text=True))
raw = base64.b64decode(result.pop("archive_base64"), validate=True)
assert hashlib.sha256(raw).hexdigest() == result["archive_SHA256"]
files = {}
with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
    for member in archive:
        path = PurePosixPath(member.name)
        assert member.isfile() and not path.is_absolute() and ".." not in path.parts and member.size < 5 * 1024 * 1024
        assert member.name not in files
        files[member.name] = archive.extractfile(member).read()
assert {name: hashlib.sha256(data).hexdigest() for name, data in files.items()} == result["members_SHA256"]
for line in files["source.sha256"].decode().splitlines():
    sha, name = line.split(maxsplit=1)
    assert hashlib.sha256(files[name]).hexdigest() == sha
args.out.mkdir(parents=True, exist_ok=True)
(args.out / ("run-" + args.tag + ".tar.gz.b64")).write_bytes(base64.encodebytes(raw))
(args.out / ("recovery-" + args.tag + ".json")).write_text(json.dumps(result, indent=2) + "\n")
recovered = args.out / ("recovered-" + args.tag)
recovered.mkdir(exist_ok=False)
for name, data in files.items():
    target = recovered / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
print(json.dumps(dict(tag=args.tag, files=len(files), all_SHA256_match=True, archive_SHA256=result["archive_SHA256"])))
