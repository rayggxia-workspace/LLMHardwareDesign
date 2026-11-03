import subprocess,shlex
code=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'route-selection-102/sready616-rejected-unadmitted-archive';assert not out.exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();tasks=json.loads((b/'route-selection-102/sready609-pattern-weight-controls/tasks.json').read_text())['tasks'];assert len(tasks)==15;rows=[]
replacement=json.loads((b/'route-selection-102/sready614-pattern-weight-controls/tasks.json').read_text())['tasks'];assert len(replacement)==15
for row in replacement:assert sha(Path(row['path']))==row['sha256']
for row in tasks:
 p=Path(row['path']);assert p.resolve().parent.name=='pending'and b in p.resolve().parents and sha(p)==row['sha256'];queue=p.parent.parent
 state=json.loads((queue/'queue-state.json').read_text());assert p.stem not in state['active'] and not(queue/'commands'/(p.stem+'.json')).exists()
 result=queue/'results'/(p.stem+'.json')
 if result.exists():
  r=json.loads(result.read_text());assert r.get('rejected_before_admission')and r['error']=='Unsupported task script'and r['returncode']==-2
 rows.append(dict(original_path=str(p),sha256=row['sha256'],queue=str(queue),rejected_result=str(result)if result.exists()else None))
out.mkdir()
for row in rows:
 p=Path(row['original_path']);target=out/'specs'/p.parent.parent.parent.name/p.parent.parent.name/p.name;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();p.rename(target);assert sha(target)==row['sha256'];row['archived_path']=str(target)
 if row['rejected_result']:
  p=Path(row['rejected_result']);raw=p.read_bytes();t=out/'rejected-result.json';t.write_bytes(raw);row['rejected_result_sha256']=sha(t)
r=dict(passed=True,time=time.time(),rows=rows,whole_system_qualified=False,scope='Retire only15 exactSHA source608 specs that were never admitted: one explicit unchanged allowlist rejection and14 dependent chains that never ran. Original specs moved byte-identically into this owned archive; raw rejection retained in original results plus copied here. Replacement source613 uses existing allowed system_upper dispatcher; closed controller allowlist unchanged. Other pending/active tasks, parent jobs, foreign/R and immutable source/output directories unchanged. This metadata repair does not qualify routing or physical results.');(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,archived_never_admitted_specs=len(rows))))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
