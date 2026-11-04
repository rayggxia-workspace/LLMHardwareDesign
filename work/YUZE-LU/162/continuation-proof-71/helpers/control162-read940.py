from pathlib import Path
import subprocess,shlex,json,hashlib,base64
h=Path(__file__).parent;out=h/'control162-frozen-disconnection940';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'r256-frozen-prefix-disconnection-readback-940';assert not record.exists();rows=[];selected=None
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for tag in [9060,9062]:
 root=b/'r256-composition-453/upper-candidates'/str(tag)/'route'
 for log in sorted(root.glob('trial-*/router.log')):
  lines=log.read_text().splitlines()
  if not lines or not lines[-1].startswith(('disconnected bidirectional tree:','frozen native prefix blocks an ordinary terminal;')):continue
  prefix=log.parent/'output.txt.native-prefix-paths.txt';plan=log.parent/'output.txt.pin-access.json';inp=log.parent/'input.txt';native=log.parent/'output.txt.native-prefix.log'
  if not all(p.exists()for p in [prefix,plan,inp,native]):continue
  d=json.loads(plan.read_text());ns=[json.loads(l)for l in native.read_text().splitlines()if 'conflict_nodes'in l];assert ns[-1]['conflict_nodes']==0
  row=dict(candidate=tag,trial=log.parent.name,failure=lines[-1],native_final=ns[-1],plan_summary={k:v for k,v in d.items()if k!='plan'},files={p.name:dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)for p in [log,prefix,plan,inp,native]});rows.append(row)
  if selected is None and tag==9060:selected=dict(row=row,files={p.name:base64.b64encode(p.read_bytes()).decode()for p in [log,prefix,plan,inp,native]})
assert selected and rows;record.mkdir();r=dict(time=time.time(),whole_system_qualified=False,route_qualified=False,rows=rows);(record/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(receipt=r,selected=selected)))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);d=json.loads(raw);out.mkdir();(out/'readback.json').write_bytes((json.dumps(d['receipt'],indent=2)+'\n').encode());selected=d['selected']
for name,data in selected['files'].items():
 raw=base64.b64decode(data);assert hashlib.sha256(raw).hexdigest()==selected['row']['files'][name]['sha256'];(out/name).write_bytes(raw)
(out/'selected.json').write_bytes((json.dumps(selected['row'],indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['receipt']['rows']),selected=selected['row']['trial'],failure=selected['row']['failure'],native_final=selected['row']['native_final'],plan=selected['row']['plan_summary'])))
