"""Collect bounded final evidence and native flow metrics; no design writes remotely."""
from pathlib import Path
import subprocess,shlex,tarfile,io,json,hashlib
R=Path(__file__).resolve().parents[3];O=R/'work/YUZE-LU/157/evidence/extended'
script=r'''
from pathlib import Path
import sys,json,hashlib,tarfile,io,gzip
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
payload={};manifest=[]
def add(p,name=None):
 data=p.read_bytes();name=name or str(p.relative_to(B));digest=hashlib.sha256(data).hexdigest();orig=dict(path=str(p),sha256=digest,bytes=len(data))
 if p.suffix in ['.log','.tsv']or p.name=='COVERAGE.json':data=gzip.compress(data);name+='.gz'
 payload[name]=data;manifest.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),remote_original=orig))
for n in range(43,61):
 root=B/('attempt%03d'%n)
 for p in (root/'results').rglob('*'):
  if not p.is_file()or any(x in p.parts for x in ['obj']):continue
  if p.name in ['mapped.json','operators.json','lowered.json','gold.json','gate.json','optimized.json','proof.json','input.v','named.v','classified.tcl']:continue
  if p.suffix not in ['.json','.log','.tsv','.csv','.vcd']:continue
  if p.suffix=='.csv'and p.name.endswith('.trace.csv')and not any(s in p.name for s in ['W0-m0-n2048-t128','W1-m0-l24-t128','W2-m0-n8192-t16','W3-t128']):continue
  if p.stat().st_size>50_000_000:continue
  add(p)
 for name in ['slurm.err','slurm.out','source-check.log','stage-check.log']:
  p=root/name
  if p.exists()and p.stat().st_size<1_000_000:add(p)
for p in (B/'attempt055/unit/c_wide_native').glob('*'):
 if p.is_file()and p.name in ['receipt.json','map.ys','map.log','test.log','build.log']:add(p)
snapshot={}
for n,c in [(20,'B256'),(40,'A0'),(44,'A1')]:
 root=B/('attempt%03d'%n)/'physical';logroot=root/'flow/logs/nangate45'/('rarch157_'+c)/'base';reproot=root/'flow/reports/nangate45'/('rarch157_'+c)/'base'
 files=list(logroot.glob('*.json'))
 snapshot[c]=dict(flow_receipt=json.loads((root/'receipt.json').read_text())if(root/'receipt.json').exists()else None,metrics={p.name:json.loads(p.read_text())for p in files})
 for p in files+[logroot/'5_2_route.log',logroot/'5_1_grt.log',reproot/'6_finish.rpt',reproot/'3_global_place.rpt']+[reproot/('final_'+s+'.webp')for s in ['congestion','routing','worst_path']]:
  if p.exists():add(p)
 for name in ['receipt.json','NETLIST_NORMALIZATION.json','config.mk','input.sdc','pins.tcl']:
  p=root/name
  if p.exists():add(p)
payload['PHYSICAL_METRICS_SNAPSHOT.json']=(json.dumps(snapshot,indent=2)+'\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|')as t:
 for name,data in payload.items():
  ti=tarfile.TarInfo(name);ti.size=len(data);t.addfile(ti,io.BytesIO(data))
 data=(json.dumps(manifest,indent=2)+'\n').encode();ti=tarfile.TarInfo('FINAL_COLLECTED.json');ti.size=len(data);t.addfile(ti,io.BytesIO(data))
'''
def main():
 data=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(script)])
 with tarfile.open(fileobj=io.BytesIO(data))as t:
  manifest=json.loads(t.extractfile('FINAL_COLLECTED.json').read())
  for row in manifest:assert hashlib.sha256(t.extractfile(row['path']).read()).hexdigest()==row['sha256']
  for m in t:
   assert not m.name.startswith('/')and'..'not in Path(m.name).parts
   p=O/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
 for p in(R/'.local/157').glob('*.json'):
  if p.name.startswith(('deployment','superseded-proof-jobs')):(O/p.name).write_bytes(p.read_bytes())
 print(json.dumps(dict(files=len(manifest),archive_bytes=len(data))))
if __name__=='__main__':main()
