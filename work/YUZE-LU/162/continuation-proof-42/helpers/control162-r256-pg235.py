"""Independently advance genuinely accepted R256 control leaves to fixed PG."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-232';record=b/'route-selection-102/sready235-r256-pg';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[];record.mkdir()
def add(node,name,script,args,deps,out,memory):
 p=b/'dynamic-02'/('node'+str(node))/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
for n,node in [(2292,7),(2294,26),(2295,26)]:
 folder=b/'r256-native-229'/str(n)/'gates/deliver';receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
 delivery=folder/'delivery.json';assert sha(delivery)==receipt['outputs']['delivery.json'];d=json.loads(delivery.read_text());assert d['passed']and d['native_leaf_accepted']
 assert set(d['gate_receipts'])=={'physical','drc','function','formal'}
 for op,r in d['gate_receipts'].items():
  p=Path(r['path']);assert sha(p)==r['sha256'];g=json.loads(p.read_text());assert g['passed']
  name={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}[op]
  p=p.parent/name;assert sha(p)==r['report_sha256']==g['outputs'][name];report=json.loads(p.read_text());assert report['passed']and report['source_receipt_sha256']==d['source_receipt_sha256']
 assert set(d['final_files'])=={'6_final.'+s for s in ['v','sdc','def','odb','spef','gds']}
 for f in d['final_files'].values():assert sha(f['path'])==f['sha256']
 pins=folder/'pins.json';assert sha(pins)==d['pins_sha256'];top=d['top']
 manifest=record/(top+'-physical.json');manifest.write_text(json.dumps(dict(leaves={top:dict(pins=str(pins),pins_sha256=sha(pins),final_files=d['final_files'],die_um=d['die_um'],selection_delivery=dict(path=str(delivery),sha256=sha(delivery),receipt=str(folder/'receipt.json'),receipt_sha256=sha(folder/'receipt.json')))},whole_system_qualified=False),indent=2))
 root=b/'r256-fixed-pg-235'/str(n);wrapper=root/'wrapper';checks=root/'checks';final=root/'delivery'
 common=['--manifest',manifest,'--leaf',top]
 add(node,'00-e-sready235-pg-'+str(n),'pg_fixed_access.py',common,[],wrapper,32)
 for mode in ['physical','timing']:
  add(node,'00-f-sready235-'+mode+'-'+str(n),'pg_fixed_timing.py',common+['--wrapper',wrapper]+(['--physical-only']if mode=='physical'else[]),[wrapper/'receipt.json'],checks/mode,32)
 add(node,'00-g-sready235-deliver-'+str(n),'pg_fixed_timing.py',common+['--wrapper',wrapper,'--deliver','--physical-check',checks/'physical','--timing-check',checks/'timing'],[checks/mode/'receipt.json'for mode in ['physical','timing']],final,32)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Three genuinely accepted leaves individually enter original fixed-PG complete DRC/XOR/native continuity/new extraction/300MHz/full-view identity/delivery chain; no global slowest-leaf barrier. Own existing node7/node26 dynamic sixteen CPU slots and original memory gate only.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record))))
'''
compile(q,'r256_pg235','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=60).decode())
