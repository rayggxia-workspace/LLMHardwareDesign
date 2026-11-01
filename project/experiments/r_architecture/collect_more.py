"""Collect bounded reports, never giant databases; hash both sides of transfer."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,tarfile,io
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'work/YUZE-LU/157/evidence'
BASE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture'
script=r"""from pathlib import Path
import json,hashlib,tarfile,sys,os,io
base=Path(BASE)
paths=[];payloads={}
for num in [1,7,9,11,12,13,14,15,16,17,18,19,20,21,22,23,24]:
 root=base/('attempt%03d'%num)
 for p in (Path(d)/f for d,ds,fs in os.walk(root) for f in fs if not set(Path(d).relative_to(root).parts)&{'work','project','obj','flow'}):
  if not p.is_file() or '/obj/'in str(p)or'/flow/'in str(p):continue
  rel=p.relative_to(root).as_posix()
  if rel.startswith(('project/','work/')):continue
  if p.name in ['mapped.json','operators.json','lowered.json','gold.json','gate.json']:continue
  if p.stat().st_size>5_000_000:continue
  if p.suffix not in ['.json','.csv','.log','.err','.out','.ys','.vcd']:continue
  if p.name in ['BUNDLE.json']:continue
  paths.append(p);payloads[p]=p.read_bytes()
manifest=[dict(path=str(p.relative_to(base)),sha256=hashlib.sha256(payloads[p]).hexdigest(),bytes=len(payloads[p]))for p in paths]
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as t:
 for p in paths:
  info=tarfile.TarInfo(str(p.relative_to(base)));info.size=len(payloads[p]);t.addfile(info,io.BytesIO(payloads[p]))
 b=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('COLLECTED.json');info.size=len(b);t.addfile(info,__import__('io').BytesIO(b))
""".replace('Path(BASE)','Path('+repr(BASE)+')')
def main():
 data=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(script)])
 with tarfile.open(fileobj=io.BytesIO(data))as t:
  manifest=json.loads(t.extractfile('COLLECTED.json').read())
  for row in manifest:
   name=row['path'];assert not name.startswith('/')and'..'not in Path(name).parts;b=t.extractfile(name).read();assert hashlib.sha256(b).hexdigest()==row['sha256'];p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 (OUT/'COLLECTED_MORE.json').write_text(json.dumps(manifest,indent=2)+'\n')
 for p in(ROOT/'.local/157').glob('deployment*.json'):(OUT/p.name).write_bytes(p.read_bytes())
 for p in(ROOT/'.local/157').glob('superseded-proof-jobs*.json'):(OUT/p.name).write_bytes(p.read_bytes())
 print(json.dumps(dict(files=len(manifest),bytes=len(data))))
if __name__=='__main__':main()
