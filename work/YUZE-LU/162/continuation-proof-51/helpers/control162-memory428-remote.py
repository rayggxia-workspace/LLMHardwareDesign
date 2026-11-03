from pathlib import Path
import json,subprocess,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-search-memory-sample-428';assert not out.exists();details=subprocess.check_output(['scontrol','show','job','95391','-o']).decode();assert 'UserId=yuzelu(10011)'in details and'JobName=yzl-ctl162-'in details and'NodeList=node4 'in details
code="""from pathlib import Path
import os,json
binary='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-359/upper-candidates/4010/route/router'
rows=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=10011:continue
  cmd=(p/'cmdline').read_bytes().decode().split(chr(0))
  if not cmd or cmd[0]!=binary:continue
  memory={k:v.strip()for k,v in(line.split(':',1)for line in(p/'status').read_text().splitlines()if ':'in line)}
  rows.append(dict(pid=int(p.name),input=cmd[1],vmrss_kib=int(memory['VmRSS'].split()[0]),vmhwm_kib=int(memory['VmHWM'].split()[0]),threads=int(memory['Threads'])))
 except(OSError,UnicodeError):pass
mem={k:v.strip()for k,v in(line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
print(json.dumps(dict(rows=rows,node_available_kib=int(mem['MemAvailable'].split()[0]))))
"""
command=['srun','--jobid=95391','--overlap','-n1','-c1','python3','-c',code];data=json.loads(subprocess.check_output(command).decode());assert data['rows']and all(r['threads']==1 for r in data['rows']);failed=[]
for p in(b/'r256-composition-359/upper-candidates/4010/route').glob('trial-*/router.log'):
 raw=p.read_bytes()
 if b'finite-resource search label memory envelope exhausted'in raw:failed.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()))
assert len(failed)>=4;out.mkdir();(out/'reader.py').write_text(code);result=dict(diagnostic_executed=True,captured_at=time.time(),job_details=details,sample=data,failed_label_limit_logs=failed,reader_sha256=hashlib.sha256(code.encode()).hexdigest(),whole_system_qualified=False,scope='Only exact own source400/4010 surviving process cmdlines/UID10011 sampled. HWM is measured for survivors, not the four exited trials; label-envelope exception is a software workspace cap, not an observed OS out-of-memory event. Optional8million bounded labels will retain16 active trials and original2GiB-per-active forecast,1.2+16GiB memory admission; actual new peak still requires observation. No physical gates changed, no concurrency reduction or foreign process actions.')
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(surviving=len(data['rows']),highest_vmhwm_kib=max(r['vmhwm_kib']for r in data['rows']),available_kib=data['node_available_kib'],label_limit_failures=len(failed))))
