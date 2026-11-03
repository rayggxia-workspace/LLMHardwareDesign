"""Recover only two failed own allocations, preserving all old artifacts."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,time,re
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-236';record=b/'route-selection-102/sready237-controller-recovery'
if record.exists():
 assert not any(record.iterdir());record.rename(record.with_name(record.name+'-incomplete-01'))
record.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();allrows=[]
active=subprocess.check_output(['squeue','-u','yuzelu','-h','-o','%i|%j'],universal_newlines=True).splitlines();own=[r for r in active if '|yzl-ctl162-'in r];assert len(own)==6,own
for node,job,cpus in [(7,'95102',64),(26,'95119',96)]:
 old=b/'dynamic-02'/('node'+str(node));out=b/'dynamic-06'/('node'+str(node))
 if out.exists():
  assert node==7 and not(out/'submission.json').exists()and not(out/'batch.sh').exists();out.rename(out.with_name(out.name+'-setup-incomplete-01'))
 assert not out.exists()
 status=subprocess.check_output(['sacct','-j',job,'-X','--format=JobID,State,NodeList','-n','-P'],universal_newlines=True);assert 'FAILED'in status and 'node'+str(node)in status
 out.mkdir(parents=True)
 for name in ['pending','commands','results']:(out/name).mkdir()
 archive=out/'previous-controller-failure';archive.mkdir()
 for name in ['slurm.log','queue-state.json','submission.json']:
  if(old/name).exists():(archive/name).write_bytes((old/name).read_bytes())
 (archive/'sacct.txt').write_text(subprocess.check_output(['sacct','-j',job,'--format=JobID,JobName,State,ExitCode,Elapsed','-n','-P'],universal_newlines=True))
 assert 'AssertionError'in(old/'slurm.log').read_text()
 def copy(p,newname,replacements=()):
  original=json.loads(p.read_text());spec=json.loads(p.read_text());text=json.dumps(spec)
  for before,after in replacements:text=text.replace(before,after)
  spec=json.loads(text);target=out/'pending'/(newname+'.json');assert not target.exists()
  args=spec['args'];dest=Path(args[args.index('--out')+1]);assert not dest.exists(),str(dest)
  target.write_text(json.dumps(spec));allrows.append(dict(original=str(p),original_sha256=sha(p),path=str(target),sha256=sha(target),spec=spec))
 # These tasks were never admitted by the failed old controller.
 for p in sorted((old/'pending').glob('*.json')):
  if '-sready233-'in p.name or '-sready235-'in p.name:
   assert not(old/'commands'/p.name).exists()and not(old/'results'/p.name).exists();copy(p,p.stem)
 # Restart interrupted C and route attempts in fresh output directories only.
 pairs=[(2291,2371)]if node==7 else[]
 for before,after in pairs:
  selected=[p for p in(old/'pending').glob('*.json')if p.stem.endswith('-'+str(before))]
  assert len(selected)==7,(before,len(selected))
  oldroot=str(b/'r256-native-229'/str(before))if before==2291 else str(b/'s-ready-composition-01/1391/upper-candidates'/str(before))
  newroot=str(b/'r256-native-237'/str(after))if before==2291 else str(b/'s-ready-composition-01/1391/upper-candidates'/str(after))
  for p in selected:copy(p,p.stem.rsplit('-',1)[0]+'-recovery237-'+str(after),[(oldroot,newroot)])
 wrapper=out/'batch.sh';wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec bash '+str(source/'project/experiments/control_v1/dynamic_queue.sh')+' '+str(source)+' '+str(out)+'\n')
 command=['sbatch','--parsable','--partition='+('c64'if cpus==64 else'c96'),'--cpus-per-task='+str(cpus),'--mem=0','--exclusive','--time=0','--no-requeue','--nodelist=node'+str(node),'--job-name=yzl-ctl162-rec237n'+str(node),'--output='+str(out/'slurm.log'),str(wrapper)]
 submitted=subprocess.check_output(command,universal_newlines=True).strip();assert submitted.isdigit();(out/'submission.json').write_text(json.dumps(dict(job=submitted,command=command,time=time.time()),indent=2));print('replacement',node,submitted)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=allrows,controller_source=str(source),controller_sha256=sha(source/'project/experiments/control_v1/dynamic_queue.py'),reason='Own old controllers asserted on newly queued physical_only.py. No old spec/output modified. Native C and interrupted routes restart fresh; genuinely completed native leaf gates retained; never-admitted retry and PG specs copied byte-semantically. Six still-running allocations plus these two replacements keep total eight, c64 four/c96 six independent sixteen-CPU dynamic slots. Original measured memory gate unchanged. No foreign job touched.',whole_system_qualified=False),indent=2))
print(json.dumps(dict(tasks=len(allrows),record=str(record))))
'''
compile(q,'recover_queues237','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
