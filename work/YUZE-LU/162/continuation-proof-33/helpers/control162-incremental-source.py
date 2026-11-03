"""Append immutable exact committed sources using the previous verified archive."""
from pathlib import Path
import subprocess,tarfile,json,hashlib,io,sys
n,previous=map(int,sys.argv[1:]);repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent
target=home/('control162-source%d.tar.gz'%n);assert not target.exists()
with tarfile.open(home/('control162-source%d.tar.gz'%previous))as old:
 members={m.name:old.extractfile(m).read()for m in old.getmembers()}
old=json.loads(members.pop('source-manifest.json'));head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo).decode().strip()
changed=subprocess.check_output(['git','diff','--name-only',old['commit'],head],cwd=repo).decode().splitlines()
for p in changed:
 if p in old['files']or p.startswith('project/'):
  members[p]=subprocess.check_output(['git','show',head+':'+p],cwd=repo)
files={p:hashlib.sha256(v).hexdigest()for p,v in members.items()}
members['source-manifest.json']=(json.dumps(dict(commit=head,files=files),indent=2)+'\n').encode()
with tarfile.open(target,'w:gz')as archive:
 for p,data in members.items():
  entry=tarfile.TarInfo(p);entry.size=len(data);entry.mode=0o644;entry.mtime=0;archive.addfile(entry,io.BytesIO(data))
print(json.dumps(dict(commit=head,files=len(files),archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),changed=changed)))
