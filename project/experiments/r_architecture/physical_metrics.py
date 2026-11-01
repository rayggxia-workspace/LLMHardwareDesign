from pathlib import Path
import subprocess,os,json,time,hashlib
P=Path(__file__).resolve().parent;BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt020/physical');OUT=Path.cwd()/'results';OUT.mkdir(exist_ok=False)
while not(BASE/'receipt.json').exists():time.sleep(15)
receipt=json.loads((BASE/'receipt.json').read_text());(OUT/'FLOW_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
root=BASE/'flow/results/nangate45/rarch157_B256/base';rows=[]
for stage in ['3_3_place_gp','5_1_grt','5_2_route','6_final']:
 p=root/(stage+'.odb')
 if not p.exists():continue
 env=os.environ.copy();env.update(INPUT_ODB=str(p),OUTPUT_JSON=str(OUT/(stage+'.json')))
 with(OUT/(stage+'.log')).open('w')as f:r=subprocess.run(['openroad','-python','-exit',str(P/'odb_probe.py')],env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(stage=stage,exit=r.returncode,odb=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(OUT/'ODB_RECEIPTS.json').write_text(json.dumps(rows,indent=2)+'\n');assert all(x['exit']==0 for x in rows)
