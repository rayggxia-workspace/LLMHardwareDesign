import subprocess,shlex
q=r'''from pathlib import Path
import json,os,hashlib,time,signal
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-local-rectangle-cut-387';p=out/'summary.json'
if p.exists():
 d=json.loads(p.read_text());print(json.dumps(dict(done=True,placements=[dict(placement=Path(r['placement']).parent.name,rectangles=r['rectangles_checked'],violated=r['violated'],worst=r['worst'][:1])for r in d['placements']])));raise SystemExit()
found=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=10011:continue
  cmd=(p/'cmdline').read_bytes().decode().split(chr(0))
  if len(cmd)>=3 and cmd[1]=='-c'and 'out=b/\'r256-local-rectangle-cut-387\';assert not out.exists();g='in cmd[2]and 'for seed in [3690,3691,3692,3693]:'in cmd[2]:found.append(dict(pid=int(p.name),command_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()))
 except (OSError,UnicodeError):pass
record=b/'r256-local-rectangle-cut-387-launch-timeout.json';assert not record.exists();record.write_text(json.dumps(dict(time=time.time(),passed=False,whole_system_qualified=False,output_exists=False,verified_own_procs=found,reason='Unoptimized all-net rectangle inspection exceeded local55s SSH bound; retain original helper, no result or infeasibility claim. Stop only exact own diagnostic process on login; rework indexed query for bounded analysis.'),indent=2))
for row in found:os.kill(row['pid'],signal.SIGTERM)
print(json.dumps(dict(done=False,stopped_verified_own_procs=found,record=str(record))))
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=20).decode())
