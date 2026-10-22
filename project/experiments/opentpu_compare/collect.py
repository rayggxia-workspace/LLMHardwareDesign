"""Read compact observations; freeze terminal receipts without changing remote data."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
receipts=sorted((HERE/'results').glob('*-submission.json'))
REMOTE_SCRIPT=r'''
from pathlib import Path
import hashlib,json,re,subprocess
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15')
out={}
def read_json(path):
 try: return json.load(open(path))
 except (ValueError,FileNotFoundError) as error: return {'collection_pending_or_invalid':str(error)}
for p in sorted(base.iterdir()):
 if not (p/'spec.json').exists(): continue
 spec=json.load(open(p/'spec.json'))
 row={'spec':spec,'exit_code':(p/'exit-code.txt').read_text().strip() if (p/'exit-code.txt').exists() else None}
 for name in ['started.txt','finished.txt','allocation.txt','resource-audit.json','experiment.json','input-sha256.json','strict-pg.json','final-pg/strict-pg.json','layer-reservation.json','transparent-sta-validation.json','resource-qualification.json','full-hierarchy-quality.json','pre-drt-electrical-quality.json','pin-placement-quality.json']:
  f=p/name
  if f.exists():
   row[name]=read_json(f) if f.suffix=='.json' else f.read_text()
 files=sorted((p/'flow/logs').rglob('*.log'),key=lambda f:f.stat().st_mtime) if (p/'flow/logs').exists() else []
 if files: row['last_flow_log']={'path':str(files[-1]),'tail':files[-1].read_text(errors='replace').splitlines()[-8:]}
 row['job_log_tail']=(p/'job.log').read_text(errors='replace').splitlines()[-14:] if (p/'job.log').exists() else []
 row['metrics']={}
 for f in (p/'flow/logs').rglob('*.json') if (p/'flow/logs').exists() else []:
  if f.name in ('6_report.json','5_2_route.json','5_1_grt.json'):
   d=read_json(f);row['metrics'][f.name]={k:v for k,v in d.items() if any(s in k for s in ['timing','area','wirelength','vias','antenna','drc','instance','violations','power','clock','net__count'])}
 for f in (p/'flow/reports').rglob('6_finish.rpt') if (p/'flow/reports').exists() else []:
  row['final_report']=f.read_text()
 for f in (p/'flow/logs').rglob('5_2_route.log') if (p/'flow/logs').exists() else []:
  tables=re.findall(r'Total wire length = ([\d.]+) um\.(.*?)Total number of vias = (\d+)\.',f.read_text(),re.S)
  if tables:
   total,body,vias=tables[-1]
   row['route_layer_wire_um']={layer:float(length) for layer,length in re.findall(r'Total wire length on LAYER (\w+) = ([\d.]+) um\.',body)}
   row['route_layer_report']={'total_um':float(total),'vias':int(vias),'scope':'Final DRT signal-route table; per-layer lengths rounded to integer um; excludes special PG'}
 for f in p.glob('*-resource.json'): row[f.name]=read_json(f)
 row['pg_access']={str(f.relative_to(p)):read_json(f) for directory in [p,p/'final-pg']
                   for f in directory.glob('*-pg-access-selection.json')}
 for name in ['repair-input-audit.json','structural-equivalence.json','pin-checkpoint-diagnostics.json','stitch-validation.json','full-hierarchy-sta.log']:
  f=p/name
  if f.exists():
   if f.suffix=='.json': row[name]=read_json(f)
   else:
    text=f.read_text(errors='replace');start=text.find('worst slack max')
    row[name]=text[start:] if start>=0 else text[-12000:]
    row[name+'_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
    row['hierarchy_annotation_summary']=[line for line in text.splitlines() if any(s in line.lower() for s in ['annotated','warning','error','unconstrained','no clock'])][:60]
 row['physical_repair_actions']={}
 for name in ['targeted-drive.tsv','macro-output-guards.tsv']:
  f=p/name
  if f.exists():
   lines=f.read_text().splitlines()
   row['physical_repair_actions'][name]={'header':lines[0] if lines else '', 'rows':lines[1:]}
 contract=p/'external-pin-contract.json';pins=p/'final-pins.tsv'
 if contract.exists():
  d=json.load(open(contract))
  row['external_pin_contract']={'count':len(d),'canonical_sha256':hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
  if pins.exists():
   lines=[line for line in pins.read_text().splitlines() if line.split('\t')[0] in d]
   names={line.split('\t')[0] for line in lines}
   row['actual_signal_pin_geometry']={'all_contract_names_present':names==set(d),'rows':len(lines),
       'canonical_sha256':hashlib.sha256(('\n'.join(sorted(lines))+'\n').encode()).hexdigest(),
       'raw_all_bterms_sha256':hashlib.sha256(pins.read_bytes()).hexdigest()}
 f=p/'output.sha256'
 if f.exists(): row['output_manifest_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();row['output_manifest_entries']=len(f.read_text().splitlines())
 out[p.name]=row
print(json.dumps(out))
'''
result=subprocess.run(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3','-'],input=REMOTE_SCRIPT,
                      text=True,capture_output=True)
if result.returncode: raise SystemExit(result.stderr)
data=json.loads(result.stdout)
ids={json.loads(p.read_text())['job_id']:p.stem.removesuffix('-submission') for p in receipts}
acct=subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','sacct -n -P -j '+','.join(ids)+' --format=JobIDRaw,State,ExitCode,Elapsed,Timelimit,AllocCPUS,NodeList'],text=True)
for line in acct.splitlines():
 parts=line.split('|')
 if parts[0] in ids and ids[parts[0]] in data: data[ids[parts[0]]]['scheduler']=line
snapshot=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=data)
(HERE/'results/latest.json').write_text(json.dumps(snapshot,indent=2)+'\n')
for name,row in data.items():
 print(name,row.get('scheduler',row['exit_code']),row.get('last_flow_log',{}).get('path','').split('/')[-1])
 if row.get('scheduler') and row['scheduler'].split('|')[1] not in ('RUNNING','PENDING') and row.get('output_manifest_sha256'):
  path=HERE/'results'/(name+'-terminal.json')
  if not path.exists(): path.write_text(json.dumps(row,indent=2)+'\n')
