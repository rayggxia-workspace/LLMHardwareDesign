from pathlib import Path
import subprocess,json,shutil,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-router-hotspot-profile-772';assert not out.exists();out.mkdir();job='95391';details=subprocess.check_output(['scontrol','show','job',job,'-o'],universal_newlines=True);assert'UserId=yuzelu(10011)'in details and'NodeList=node4 'in details and'JobName=yzl-ctl162-'in details
code=r'''from pathlib import Path
import os,subprocess,json,shutil,time
out=Path(OUT);binary='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates/7370/route/router';found=[]
for n in os.listdir('/proc'):
 if not n.isdigit():continue
 try:
  p='/proc/'+n
  if os.stat(p).st_uid!=10011 or os.readlink(p+'/exe')!=binary:continue
  cmd=open(p+'/cmdline','rb').read().decode().split(chr(0))
  if any('/trial-0/input.txt' in x for x in cmd):found.append(dict(pid=int(n),command=cmd,affinity=sorted(os.sched_getaffinity(int(n)))))
 except OSError:pass
assert len(found)==1;target=found[0];perf=shutil.which('perf');r=dict(time=time.time(),target=target,perf=perf,whole_system_qualified=False,scope='Non-pausing owner-only5s software CPU profile, compute node4 within own95391 allocation; no source/spec/output/memory/physical gate changes, no foreign PID touched.')
if perf:
 args=[perf,'record','-F','99','-e','cpu-clock:u','--call-graph','dwarf','-p',str(target['pid']),'-o',str(out/'perf.data'),'--','sleep','5'];v=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE);r.update(record_returncode=v.returncode,record_command=args);(out/'record.stdout').write_bytes(v.stdout);(out/'record.stderr').write_bytes(v.stderr)
 if v.returncode==0:
  args=[perf,'report','--stdio','--no-children','-i',str(out/'perf.data'),'--percent-limit','1'];v=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE);r.update(report_returncode=v.returncode);(out/'report.stdout').write_bytes(v.stdout);(out/'report.stderr').write_bytes(v.stderr)
else:r['unavailable_reason']='perf binary not installed; no installation or permission change attempted'
(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(pid=target['pid'],perf=perf,record_returncode=r.get('record_returncode'),report_returncode=r.get('report_returncode'),unavailable_reason=r.get('unavailable_reason'))))
'''.replace('OUT',repr(str(out)))
compile(code,'computeprofile772','exec');z=subprocess.run(['srun','--jobid='+job,'--overlap','-n1','-c1','python3','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE);(out/'launcher.stdout').write_bytes(z.stdout);(out/'launcher.stderr').write_bytes(z.stderr);assert z.returncode==0;print(z.stdout.decode())
