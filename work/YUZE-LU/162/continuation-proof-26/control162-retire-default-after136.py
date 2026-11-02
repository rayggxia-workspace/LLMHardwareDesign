"""Retire only the exact redundant S1350 default compile after real new passes."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');g=b/'s-escape-gates-02/1350';old=b/'s-escape-gates-01/1350/function'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for part in iter(lambda:f.read(16*1024*1024),b''):h.update(part)
 return h.hexdigest()
fr=json.loads((g/'function/receipt.json').read_text());rr=json.loads((g/'formal/receipt.json').read_text());assert fr['passed']and rr['passed']
fn=json.loads((g/'function/final-function.json').read_text());fo=json.loads((g/'formal/formal.json').read_text())
assert sha(g/'function/final-function.json')==fr['outputs']['final-function.json']and sha(g/'formal/formal.json')==rr['outputs']['formal.json']
assert fn['passed']and fo['passed']and all(fo['strict_native_lec']['checks'].values())
assert fo['function_receipt_sha256']==sha(g/'function/receipt.json')
view=json.loads((old/'physical-functional-proof.json').read_text());assert view['passed']
assert view['full_view_sha256']==fn['full_final_netlist']['full_view_sha256']and view['input_sha256']==fn['full_final_netlist']['input_sha256']
assert sha(view['full_view'])==view['full_view_sha256']==sha(fn['full_final_netlist']['full_view'])
assert sha(b/'source-135/project/experiments/control_v1/test_native_s.cpp')==fn['bench_sha256']
queue=b/'dynamic-05/node2';state=json.loads((queue/'queue-state.json').read_text());name='00-b-s1350-function'
if name not in state['active']:print(json.dumps(dict(retired=False,reason='Exact old default function is no longer active; nothing cancelled.')));raise SystemExit(0)
spec_path=queue/'pending'/(name+'.json');spec=json.loads(spec_path.read_text())
assert spec['script']=='gates.py'and spec['args'][0]=='function'and spec['source_root']==str(b/'source-135')
assert spec['args'][spec['args'].index('--out')+1]==str(old)
job=95341;details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-smem2 'in details and 'NodeList=node2 'in details
text=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True)
found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',text)]
code="import os,json;d={}\nfor p in "+repr([r[2]for r in found])+":\n try:\n  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))\n except OSError:pass\nprint(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
for step,node,pid in found:
 args=procs.get(pid,[])
 if '--out'in args and args[args.index('--out')+1]==str(old)and str(b/'source-135/project/experiments/control_v1/gates.py')in args and 'function'in args:targets.append(dict(step=step,node=node,pid=pid,args=args))
assert len(targets)==1,targets
root=b/'route-selection-102/s1350-default-retire-after136';assert not root.exists();root.mkdir()
record=dict(time=time.time(),job=job,job_details=details,spec_path=str(spec_path),spec_sha256=sha(spec_path),target=targets[0],
 exact_complete_view_sha256=view['full_view_sha256'],function_receipt_sha256=sha(g/'function/receipt.json'),formal_receipt_sha256=sha(g/'formal/receipt.json'),
 reason='New S1350 exact complete-view/bench actual three-initial function and strict all-boundary formal genuinely passed. Stop only redundant old default compilation, retain every original artifact/spec and record it incomplete, never a physical failure. Actual native/full-deck/PG checks and all parents/other tasks untouched.')
(root/'verified-before.json').write_text(json.dumps(record,indent=2))
result=subprocess.run(['scancel',targets[0]['step']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'],returncode=result.returncode,stdout=result.stdout,stderr=result.stderr),indent=2));assert result.returncode==0
print(json.dumps(dict(retired_exact_own_step=targets[0]['step'],original_attempt='incomplete redundant compilation, not hardware failure',record=str(root))))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
