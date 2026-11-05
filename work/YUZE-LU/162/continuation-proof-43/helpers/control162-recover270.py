import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,time,re,shutil
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'dynamic-06/node7';new=b/'dynamic-07/node7';source=b/'source-269';record=b/'route-selection-102/sready270-controller-recovery';assert not new.exists()and not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
status=subprocess.check_output(['sacct','-j','96221','-X','--format=JobID,State,NodeList','-n','-P'],universal_newlines=True);assert 'FAILED'in status and 'node7'in status
assert "name=path.stem;assert re.fullmatch"in(old/'slurm.log').read_text()
active=[s for s in subprocess.check_output(['squeue','-u','yuzelu','-h','-o','%i|%j'],universal_newlines=True).splitlines()if '|yzl-ctl162-'in s];assert len(active)==7,active
new.mkdir(parents=True);record.mkdir()
for n in ['pending','commands','results','previous-controller-failure']:(new/n).mkdir()
for n in ['slurm.log','queue-state.json','submission.json']:shutil.copyfile(old/n,new/'previous-controller-failure'/n)
(new/'previous-controller-failure/sacct.txt').write_text(subprocess.check_output(['sacct','-j','96221','--format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS','-P'],universal_newlines=True))
state=json.loads((old/'queue-state.json').read_text());interrupted=set(state['active']);assert interrupted=={'00-e-sready257-pg-r256','00-c-sready259-eight-final-programs','00-e-sready261-pg-2371'}
replacements=[(str(b/'r256-fixed-pg-261/2371'),str(b/'r256-fixed-pg-271/2371')),(str(b/'r256-fixed-pg-257'),str(b/'r256-fixed-pg-272')),(str(b/'r256-composition-259/function'),str(b/'r256-composition-273/function')),(str(b/'r256-composition-263'),str(b/'r256-composition-274'))]
# Only the final function output path changes; completed function-inputs must
# keep their original exact paths, not the shared textual 'function' prefix.
def substitute(text):
 for before,after in replacements:
  if before.endswith('259/function'):
   text=text.replace(before+'"',after+'"').replace(before+'/',after+'/')
  else:text=text.replace(before,after)
 return text
finalold=b/'r256-composition-263';finalnew=b/'r256-composition-274';assert not finalnew.exists();finalnew.mkdir();(finalnew/'fixed-pg-wrappers').mkdir()
for n in ['configurations.json','native-cap-config.json']:(finalnew/n).write_text(substitute((finalold/n).read_text()))
for p in(finalold/'fixed-pg-wrappers').iterdir():
 assert p.is_symlink();target=str(p.readlink())if hasattr(p,'readlink')else str(Path(subprocess.check_output(['readlink',str(p)],universal_newlines=True).strip()))
 target=substitute(json.dumps(target));(finalnew/'fixed-pg-wrappers'/p.name).symlink_to(json.loads(target))
rows=[]
for p in sorted((old/'pending').glob('*.json')):
 name=p.stem
 if name in state['finished']:continue
 if (old/'commands'/p.name).exists():assert name in interrupted,name
 raw=p.read_bytes();spec=json.loads(substitute(raw.decode()));args=spec['args'];dest=Path(args[args.index('--out')+1]);assert not dest.exists(),str(dest)
 selected=Path(spec['source_root']);assert selected.parent==b and re.fullmatch('source-[0-9]+',selected.name)and(selected/'source-manifest.json').exists()
 name=name.lower();assert re.fullmatch('[a-z0-9_-]+',name);target=new/'pending'/(name+'.json');assert not target.exists();target.write_text(json.dumps(spec));rows.append(dict(original=str(p),original_sha256=sha(p),path=str(target),sha256=sha(target),spec=spec,previous_step_interrupted=p.stem in interrupted))
wrapper=new/'batch.sh';wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec bash '+str(source/'project/experiments/control_v1/dynamic_queue.sh')+' '+str(source)+' '+str(new)+'\n')
command=['sbatch','--parsable','--partition=c64','--cpus-per-task=64','--mem=0','--exclusive','--time=0','--no-requeue','--nodelist=node7','--job-name=yzl-ctl162-rec270n7','--output='+str(new/'slurm.log'),str(wrapper)]
job=subprocess.check_output(command,universal_newlines=True).strip();assert job.isdigit();(new/'submission.json').write_text(json.dumps(dict(job=job,command=command,time=time.time()),indent=2))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,new_job=job,source_manifest_sha256=sha(source/'source-manifest.json'),previous_failure='uppercase R in new queued spec name asserted before robust rejection branch',reason='Queue source269 now rejects invalid new names/scripts/source roots while active fake step survives three rejected tasks; actual regression passed. Three interrupted computations retry only in fresh paths271/272/273; all previous files/partial builds/DRC reports remain. Completed five control deliveries and C native gates untouched; future final scene rebound274. No acceptance inferred. Six other running allocations plus existing pending node26 plus this replacement remain at most eight parents; original4x16/6x16 dynamic and measured memory gates unchanged.',whole_system_qualified=False),indent=2));print(json.dumps(dict(replacement_job=job,requeued=len(rows),interrupted_restarted_fresh=3,record=str(record))))
'''
compile(q,'recover270','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
