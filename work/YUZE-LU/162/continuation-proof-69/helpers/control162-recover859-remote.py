from pathlib import Path
import json,hashlib,subprocess,time,re,shutil
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'dynamic-02/node6';new=b/'dynamic-08/node6';source=b/'source-269';record=b/'route-selection-102/sready859-controller-recovery'
if new.exists():
 assert not(new/'batch.sh').exists()and not(new/'submission.json').exists()and not any((new/'pending').iterdir());archived=new.with_name(new.name+'-setup-incomplete-01');assert not archived.exists();new.rename(archived)
if record.exists():
 assert not any(record.iterdir());record.rename(record.with_name(record.name+'-setup-incomplete-01'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
status=subprocess.check_output(['sacct','-j','95101','-X','--format=JobID,State,NodeList','-n','-P'],universal_newlines=True);assert 'FAILED'in status and 'node6'in status
failure=(old/'slurm.log').read_text();assert "source_manifest=selected_root/'source-manifest.json';assert source_manifest.is_file()"in failure
active=[s for s in subprocess.check_output(['squeue','-u','yuzelu','-h','-o','%i|%j'],universal_newlines=True).splitlines()if '|yzl-ctl162-'in s];assert len(active)==7,active
assert (b/'source-854/freeze-import.json').is_file()and(b/'source-854/source-manifest.json').is_file()
new.mkdir(parents=True);record.mkdir()
for n in ['pending','commands','results','previous-controller-failure']:(new/n).mkdir()
for n in ['slurm.log','queue-state.json','submission.json']:
 if(old/n).exists():shutil.copyfile(old/n,new/'previous-controller-failure'/n)
(new/'previous-controller-failure/sacct.txt').write_text(subprocess.check_output(['sacct','-j','95101','--format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS','-P'],universal_newlines=True))
state=json.loads((old/'queue-state.json').read_text());assert set(state['active'])=={'00-g-sready501-r256-route-5010','00-g-sready635-r256-route-6361','00-g-sready829-r256-route-8300'}
rows=[];root=b/'r256-composition-453'
for before,after in [(5010,8590),(6361,8591),(8300,8592)]:
 oldpath=root/'upper-candidates'/str(before);newpath=root/'upper-candidates'/str(after);assert not newpath.exists()
 config=root/('acceptance-'+str(before)+'.json');target=root/('acceptance-'+str(after)+'.json');assert config.is_file()and not target.exists();target.write_text(config.read_text().replace(str(oldpath)+'/',str(newpath)+'/'))
 selected=[]
 for p in(old/'pending').glob('*.json'):
  spec=json.loads(p.read_text());args=spec['args']
  if '--out'not in args:continue
  out=Path(args[args.index('--out')+1])
  if oldpath not in out.parents:continue
  assert p.stem not in state['finished'];selected.append(p)
 assert len(selected)==7,(before,len(selected))
 for p in selected:
  spec=json.loads(p.read_text());text=json.dumps(spec).replace(str(oldpath)+'/',str(newpath)+'/').replace('acceptance-'+str(before)+'.json','acceptance-'+str(after)+'.json');spec=json.loads(text)
  dest=Path(spec['args'][spec['args'].index('--out')+1]);assert not dest.exists()
  name=p.stem.replace(str(before),str(after))+'-recovery859';target=new/'pending'/(name+'.json');assert not target.exists();target.write_text(json.dumps(spec));rows.append(dict(original=str(p),original_sha256=sha(p),path=str(target),sha256=sha(target),spec=spec,interrupted=p.stem in state['active']))
p=old/'pending/00-l-sready855-native-prefix-regression.json';assert not(old/'commands'/p.name).exists()and not(old/'results'/p.name).exists();spec=json.loads(p.read_text());out=Path(spec['args'][spec['args'].index('--out')+1]);assert not out.exists();target=new/'pending'/p.name;target.write_bytes(p.read_bytes());rows.append(dict(original=str(p),original_sha256=sha(p),path=str(target),sha256=sha(target),spec=spec,never_admitted=True))
wrapper=new/'batch.sh';wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec bash '+str(source/'project/experiments/control_v1/dynamic_queue.sh')+' '+str(source)+' '+str(new)+'\n')
command=['sbatch','--parsable','--partition=c64','--cpus-per-task=64','--mem=0','--exclusive','--time=0','--no-requeue','--nodelist=node6','--job-name=yzl-ctl162-rec859n6','--output='+str(new/'slurm.log'),str(wrapper)]
job=subprocess.check_output(command,universal_newlines=True).strip();assert job.isdigit();(new/'submission.json').write_text(json.dumps(dict(job=job,command=command,time=time.time()),indent=2))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,new_job=job,source_manifest_sha256=sha(source/'source-manifest.json'),previous_failure='Own source855 regression spec was queued while source854 freezing was still running, old source62 queue asserted before source manifest existed. Other7 parents unchanged. This sequencing mistake caused parent95101 exit and its3 own steps to receive SIGTERM; not an SSH, resource or physical failure.',reason='Use already regression-qualified source269 robust queue. Copy every raw failure/old status/accounting. Three interrupted complete7stage chains restart fresh8590/8591/8592 with same original sources/parameters/inputs/physical gates; original output paths and failed/partial files untouched. Never-admitted855 waits now fully frozen854. At most8 parents,4x16 dynamic;192GiB worst active forecast needs246.4GiB actualMemAvailable; scheduler performs fresh memory admission. No externalR/foreign job touched. Future publication/queues must await freeze completion and verify manifest before enqueue.',whole_system_qualified=False),indent=2));print(json.dumps(dict(replacement_job=job,requeued=len(rows),interrupted_restarted_fresh=3,record=str(record))))
