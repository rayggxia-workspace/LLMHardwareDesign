"""Export canonical Git blobs, never working-tree EOL conversions."""
import argparse,hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:
        m=json.loads((a.verify/'source-manifest.json').read_text())
        for name,digest in m['files'].items():assert sha((a.verify/name).read_bytes())==digest,name
        print(json.dumps(dict(passed=True,commit=m['commit'],files=len(m['files']))));return
    assert a.out and not a.out.exists()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'commit before freezing source'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    entries=subprocess.check_output(['git','ls-tree','-rz','--full-tree','HEAD','project'],cwd=ROOT).split(b'\0')
    files={};contents={}
    for entry in entries:
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob'
        path=name.decode('utf-8');data=subprocess.check_output(['git','cat-file','blob',oid.decode()],cwd=ROOT)
        contents[path]=data;files[path]=sha(data)
    contents['source-manifest.json']=(json.dumps(dict(commit=commit,files=files),indent=2)+'\n').encode()
    with tarfile.open(a.out,'w:gz') as t:
        for name,data in sorted(contents.items()):
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(data))
    print(json.dumps(dict(commit=commit,files=len(files),archive_sha256=sha(a.out.read_bytes()))))
if __name__=='__main__':main()
