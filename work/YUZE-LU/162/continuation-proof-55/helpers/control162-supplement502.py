from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');out=r/'work/YUZE-LU/162/continuation-proof-55';index=out/'index.json';d=json.loads(index.read_text(encoding='utf-8'));assert not d.get('final_program_supplement')
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths=[]
for folder in ['r256-composition-453/function','r256-padding-final-function-audit-472','route-selection-102/sready473-padding-program-events','r256-bidirectional-search-regression-500']:
 for p in(b/folder).glob('*.json'):
  if p.is_file():paths.append(p)
assert json.loads((b/'r256-composition-453/function/receipt.json').read_text())['passed'];assert json.loads((b/'r256-padding-final-function-audit-472/receipt.json').read_text())['passed'];rows=[]
for p in sorted(paths):
 data=p.read_bytes();rows.append(dict(relative='final-program-supplement/'+str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),base64=base64.b64encode(data).decode(),capture_time=time.time(),active_prefix_snapshot=False))
print(json.dumps(rows))
'''
rows=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]));existing={x['relative']for x in d['rows']}
for row in rows:
 assert row['relative']not in existing;raw=base64.b64decode(row.pop('base64'));assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);row['copied']=True;d['rows'].append(row)
p=Path(__file__);raw=p.read_bytes();rel='helpers/'+p.name;(out/rel).write_bytes(raw);d['helpers'].append(dict(relative=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));d['final_program_supplement']=dict(time=time.time(),rows=len(rows),scope='Separate final453 function and independent472 audit cut. Preserve earlier live snapshots verbatim, no overwriting. 473 trace queued only; no full upper qualification.')
index.write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(added_rows=len(rows),total_rows=len(d['rows']),helpers=len(d['helpers']))))
