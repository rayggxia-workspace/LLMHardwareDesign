import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import hashlib,re,time
queue=b/'dynamic-07/node7';source=b/'source-290';record=b/'route-selection-102/sready291-r256-empty-passive';assert not record.exists();record.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((queue/'queue-state.json').read_text());rows=[]
for old,new in [('00-f-sready257-timing-r256','00-f-sready291-timing-r256'),('00-g-sready257-deliver-r256','00-g-sready291-deliver-r256')]:
 p=queue/'pending'/(old+'.json');spec=json.loads(p.read_text());spec['source_root']=str(source)
 text=json.dumps(spec).replace(str(b/'r256-fixed-pg-272/checks/timing'),str(b/'r256-fixed-pg-291/checks/timing')).replace(str(b/'r256-fixed-pg-272/delivery'),str(b/'r256-fixed-pg-291/delivery'));spec=json.loads(text)
 dest=Path(spec['args'][spec['args'].index('--out')+1]);assert not dest.exists();target=queue/'pending'/(new+'.json');assert re.fullmatch('[a-z0-9_-]+',new)and not target.exists();tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(target);rows.append(dict(path=str(target),sha256=sha(target),spec=spec,previous=str(p),previous_sha256=sha(p)))
config=b/'r256-composition-274/configurations.json';fresh=config.with_name('configurations291.json');assert not fresh.exists();fresh.write_text(config.read_text().replace(str(b/'r256-fixed-pg-272/delivery'),str(b/'r256-fixed-pg-291/delivery')))
p=queue/'pending/00-a-sready263-qualified-selection.json';assert not(queue/'commands'/p.name).exists()and p.stem not in state['active'];raw=p.read_bytes();(record/'original-selection.json').write_bytes(raw)
spec=json.loads(raw.decode().replace(str(config),str(fresh)).replace(str(b/'r256-fixed-pg-272/delivery'),str(b/'r256-fixed-pg-291/delivery')));tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.replace(p)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,selection=dict(path=str(p),sha256=sha(p),original_sha256=hashlib.sha256(raw).hexdigest()),configuration=dict(path=str(fresh),sha256=sha(fresh)),whole_system_qualified=False,reason='Actual R has zero ANTENNA_X1. Old timing stopped on nonempty-inventory assertion, despite complete whole-native/GDS DRC and actual PG continuity passed. Source290 applies unchanged strict receiver to every original endpoint with no exclusions; five positive/negative tests passed. Retry only fresh RC/timing and delivery paths, reuse exact accepted wrapper272/physical; old failed raw retained. No new allocation or gate relaxation.'),indent=2));print('queued',len(rows),'selection rebound',str(fresh))
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
