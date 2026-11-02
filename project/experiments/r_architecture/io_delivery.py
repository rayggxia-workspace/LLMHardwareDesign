"""Read-only paired native macro-pin and added-buffer supply verification."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,re,subprocess
p=argparse.ArgumentParser()
for n in ['old','new','candidate']:p.add_argument('--'+n,required=True)
p.add_argument('--expected',type=int,required=True);p.add_argument('--allocation',type=int,required=True)
a=p.parse_args();assert all(re.fullmatch(r'attempt[0-9]+',n)for n in[a.old,a.new]);assert re.fullmatch(r'[A-Za-z0-9]+',a.candidate)
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');out=Path.cwd()/'results';out.mkdir(exist_ok=False)
script=Path(__file__).parent/'io_delivery_probe.tcl'
def sha(f):
 h=hashlib.sha256()
 with f.open('rb')as s:
  for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(tag,trial,expected):
 root=base/trial/'physical';r=json.loads((root/'receipt.json').read_text());assert r['exit']==0 and r['candidate']==a.candidate
 odb=root/'flow/results/nangate45'/('rarch157_'+a.candidate)/'base/6_final.odb'
 before=sha(odb);env=os.environ.copy();env.update(INPUT_ODB=str(odb),OUTPUT_IO_TSV=str(out/(tag+'.tsv')),EXPECTED_IO_BUFFERS=str(expected))
 cmd=['openroad','-exit',str(script)]
 with(out/(tag+'.log')).open('w')as f:s=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert before==sha(odb)
 rows=[line.split('\t')for line in(out/(tag+'.tsv')).read_text().splitlines()]if(out/(tag+'.tsv')).exists()else[]
 return dict(trial=trial,exit=s.returncode,odb=str(odb),odb_sha256=before,command=cmd,rows=rows,tsv_sha256=sha(out/(tag+'.tsv'))if rows else None)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 f=pool.submit(run,'old',a.old,0);g=pool.submit(run,'new',a.new,a.expected);old,new=f.result(),g.result()
pins=lambda r:sorted(v for v in r['rows']if v[0]=='PIN')
buffers=[v for v in new['rows']if v[0]=='BUF']
passed=old['exit']==new['exit']==0 and bool(pins(old))and pins(old)==pins(new)and len(buffers)==a.expected and all(v[4:6]==['VDD','VSS']for v in buffers)
report=dict(passed=passed,scope='actual signal-pin coordinates and added-buffer supply connections; not complete physical acceptance',allocation=a.allocation,expected_new_buffers=a.expected,actual_new_buffers=len(buffers),signal_pin_shapes=len(pins(new)),signal_pin_geometry_identical=pins(old)==pins(new),all_added_buffer_supplies_correct=bool(buffers)and all(v[4:6]==['VDD','VSS']for v in buffers),probe_sha256=sha(script),old={k:v for k,v in old.items()if k!='rows'},new={k:v for k,v in new.items()if k!='rows'})
(out/'IO_DELIVERY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(0 if passed else 1)
