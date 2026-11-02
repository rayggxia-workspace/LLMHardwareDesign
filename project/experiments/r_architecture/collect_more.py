"""Collect bounded reports, never giant databases; hash both sides of transfer."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,tarfile,io
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'work/YUZE-LU/157/evidence/extended'
BASE='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture'
script=r"""from pathlib import Path
import json,hashlib,tarfile,sys,os,io,gzip
base=Path(BASE)
paths=[];payloads={};originals={}
for num in [1,7,9,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42]:
 root=base/('attempt%03d'%num)
 for p in (Path(d)/f for d,ds,fs in os.walk(root) for f in fs if not set(Path(d).relative_to(root).parts)&{'work','project','obj','flow'}):
  if not p.is_file()or'/obj/'in str(p):continue
  rel=p.relative_to(root).as_posix()
  if rel.startswith(('project/','work/')):continue
  if p.name in ['mapped.json','operators.json','lowered.json','gold.json','gate.json','optimized.json','proof.json']:continue
  metric='/physical/flow/'in str(p)and p.suffix in ['.json','.rpt']
  if '/flow/'in str(p)and not metric:continue
  if p.name.endswith('.trace.csv')and not any(x in p.name for x in ['W0-m0-n2048-t128','W1-m0-l24-t128','W2-m0-n8192-t16','W3-t128']):continue
  if '/a0_'in str(p)or'/a1_'in str(p)or'/a2_'in str(p):
   if p.name not in ['build.log','build_receipt.json']and not p.name.endswith('.trace.csv'):continue
  large_proof=num>=23 and ('-proof/'in str(p))and p.name in ['complete.log','STATE_RELATION.json','COVERAGE.json']
  if p.stat().st_size>5_000_000 and not large_proof:continue
  if p.suffix not in ['.json','.csv','.tsv','.log','.err','.out','.ys','.vcd']:continue
  if p.name in ['BUNDLE.json']:continue
  data=p.read_bytes();name=str(p.relative_to(base));originals[name]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data));name=name+'.gz'if large_proof else name;paths.append(name);payloads[name]=gzip.compress(data)if large_proof else data
manifest=[dict(path=p,sha256=hashlib.sha256(payloads[p]).hexdigest(),bytes=len(payloads[p]),remote_original=originals[p[:-3]if p.endswith('.gz')else p])for p in paths]
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as t:
 for p in paths:
  info=tarfile.TarInfo(p);info.size=len(payloads[p]);t.addfile(info,io.BytesIO(payloads[p]))
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
