from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-62';assert not out.exists()
code=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-pattern-weight-regression-614','r256-eighth-node-active-pool-audit-621','r256-pattern-weight-active-pool-audit-623','r256-final-chain-binding-audit-625']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
for name in ['sready609-pattern-weight-controls','sready610-pattern-weight-refill-node4','sready614-pattern-weight-controls','sready615-pattern-weight-refill-node25','sready616-rejected-unadmitted-archive']:files+=list((b/'route-selection-102'/name).rglob('*'))
for n in [608,613]:files += [b/('source-'+str(n))/'source-manifest.json',b/('source-'+str(n))/'freeze-import.json']
files += [b/'dynamic-06/node26/queue-state.json',b/'dynamic-06/node26/source-verification.json',b/'dynamic-05/node4/results/00-f-sready609-pattern-weight-regression.json']
for queue,seeds in [('dynamic-06/node26',list(range(5490,5496))),('dynamic-05/node4',[6140]),('dynamic-04/node25',[6141])]:
 for p in (b/queue/'commands').glob('*.json'):
  if any(p.stem.endswith('-'+str(seed))for seed in seeds):files.append(p)
tasks=json.loads((b/'route-selection-102/sready614-pattern-weight-controls/tasks.json').read_text())['tasks'];files += [Path(x['path'])for x in tasks]
files += [b/'r256-composition-453'/('acceptance-'+str(n)+'.json')for n in [6140,6141]]
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h']and len(raw)<1000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],timeout=45));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
d['helpers']=[]
names=['read607.py','queue609-remote.py','prepare610.py','refill610-remote.py','prepare614.py','queue614-remote.py','refill615-remote.py','archive616.py','watch618.py','read619.py','read620.py','prepare621.py','audit621.py','prepare622.py','audit622.py','audit623.py','read624.py','prepare625.py','config625-remote.py','proof626.py']
items={('helpers/control162-'+n):h/('control162-'+n)for n in names}
for n in [606,611,617]:items['helpers/publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for directory in ['control162-watch601','control162-watch618']:
 snapshots=sorted((h/directory).glob('*.json'))
 for p in [snapshots[0],snapshots[-1]]:items['selected-running-snapshots/'+directory+'/'+p.name]=p
for name,p in items.items():
 raw=p.read_bytes();t=out/name;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['metadata_failures']=dict(queue609='Closed unchanged controller allowlist rejected new standalone script before admission;1 rejected and14 never-admitted dependent specs preserved/moved exactSHA in616; replaced by source613 existing system_upper dispatcher and actual614 successful9cases.',audit622='Embedded helper syntax error before remote execution; original helper retained. No remote audit directory or running task modified.',audit623_initial='Precondition failed before output creation while6141 actual inputs still being generated. Later after all32 inputs existed, same corrected audit623 passed32 comparisons and32 actual PIDs.')
d['scope']='Actual source613 nine-case weight preflight and32PID/input comparison,96PID/disjoint6x16/memory audit on actual eighth hostnode24, both complete7stage binding configs, exact own old359 reallocations and preserved rejected/unadmitted repair. Full physical combinations remain unqualified; running snapshots selected, not complete route traces.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
