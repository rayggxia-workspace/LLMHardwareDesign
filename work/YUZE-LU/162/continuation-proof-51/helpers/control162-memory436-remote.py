from pathlib import Path
import json,subprocess,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-search-memory-sample-436';assert not out.exists();details=subprocess.check_output(['scontrol','show','job','95101','-o']).decode();assert 'UserId=yuzelu(10011)'in details and'JobName=yzl-ctl162-'in details and'NodeList=node6 'in details
code="""from pathlib import Path
import os,json
binary='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-359/upper-candidates/4300/route/router'
rows=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=10011:continue
  cmd=(p/'cmdline').read_bytes().decode().split(chr(0))
  if not cmd or cmd[0]!=binary:continue
  assert '--resource-labels=8000000'in cmd
  memory={k:v.strip()for k,v in(line.split(':',1)for line in(p/'status').read_text().splitlines()if ':'in line)}
  rows.append(dict(pid=int(p.name),input=cmd[1],vmrss_kib=int(memory['VmRSS'].split()[0]),vmhwm_kib=int(memory['VmHWM'].split()[0]),threads=int(memory['Threads'])))
 except(OSError,UnicodeError):pass
mem={k:v.strip()for k,v in(line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
print(json.dumps(dict(rows=rows,node_available_kib=int(mem['MemAvailable'].split()[0]))))
"""
command=['srun','--jobid=95101','--overlap','-n1','-c1','python3','-c',code];data=json.loads(subprocess.check_output(command).decode());assert data['rows']and all(r['threads']==1 for r in data['rows']);failed=[]
for p in(b/'r256-composition-359/upper-candidates/4300/route').glob('trial-*/router.log'):
 raw=p.read_bytes()
 if b'finite-resource search label memory envelope exhausted'in raw:failed.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()))
out.mkdir();(out/'reader.py').write_text(code);result=dict(diagnostic_executed=True,captured_at=time.time(),job_details=details,sample=data,failed_label_limit_logs=failed,reader_sha256=hashlib.sha256(code.encode()).hexdigest(),whole_system_qualified=False,scope='Actual new source429/4300 explicit8million-label processes/UID10011 sampled and actual argv checked. HWM covers currently surviving attempts only, not exited or future whole-run peaks. Still16active width/64finite attempts and original2GiB-per-active forecast/memory admission; label-limit aborts remain search failures, not physical or OS OOM evidence. All actual geometry/PG/RC300MHz gates unchanged and no concurrency reduction/foreign actions.')
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(surviving=len(data['rows']),highest_vmhwm_kib=max(r['vmhwm_kib']for r in data['rows']),available_kib=data['node_available_kib'],label_limit_failures=len(failed))))
