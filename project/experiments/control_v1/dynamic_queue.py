"""Six independent 16-CPU Slurm steps, append-only work and measured memory admission."""
import hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
root,out,image=sys.argv[1:];root=Path(root);out=Path(out)
assert os.environ.get('SLURM_JOB_ID') and int(os.environ['SLURM_CPUS_PER_TASK']) in (64,96)
slots=min(6,int(os.environ['SLURM_CPUS_PER_TASK'])//16)
assert out.is_dir() and (out/'pending').is_dir()
allowed={'pg_fixed_access.py','pg_fixed_timing.py','topology.py','system_sta.py','final_composition.py','select_leaves.py','system_upper.py','system_geometry.py','run.py','gates.py','strong_driver_audit.py'}
active={};finished={};seen={};logs={};job=os.environ['SLURM_JOB_ID']
while True:
    for name,pair in list(active.items()):
        process,spec=pair;rc=process.poll()
        if rc is not None:
            finished[name]=dict(returncode=rc,finished=time.time(),spec_sha256=seen[name]);logs[name].close();del active[name]
            (out/'results'/ (name+'.json')).write_text(json.dumps(finished[name],indent=2)+'\n')
    pending=[];transient_dependencies=[]
    for path in sorted((out/'pending').glob('*.json')):
        name=path.stem;assert re.fullmatch(r'[a-z0-9_-]+',name)
        # A never-admitted task may have been moved after glob enumerated it.
        # Even pausing this controller cannot discard its pre-pause iterator.
        # Read once: the digest and parsed specification must be the same bytes.
        try:raw=path.read_bytes()
        except FileNotFoundError:continue
        digest=hashlib.sha256(raw).hexdigest()
        if name in seen:assert seen[name]==digest,'Queued work changed after admission'
        if name in active or name in finished:continue
        # Reject invalid *new* work without taking unrelated running steps
        # down with the controller. The allowlist remains closed; rejection
        # is an explicit failed task, never a successful result or admission.
        try:
            spec=json.loads(raw);assert spec['script'] in allowed,'Unsupported task script'
            assert isinstance(spec['forecast_gib'],int) and 0<spec['forecast_gib']<=128
            assert isinstance(spec['args'],list)and all(isinstance(v,str)for v in spec['args'])
            assert isinstance(spec.get('requires',[]),list)and all(isinstance(v,str)for v in spec.get('requires',[]))
        except (AssertionError,KeyError,TypeError,json.JSONDecodeError)as error:
            finished[name]=dict(returncode=-2,rejected_before_admission=True,error=str(error),spec_sha256=digest)
            seen[name]=digest
            (out/'results'/(name+'.json')).write_text(json.dumps(finished[name],indent=2)+'\n')
            continue
        blocked=False;failed=[]
        for required in spec.get('requires',[]):
            receipt=Path(required)
            if not receipt.exists():blocked=True;continue
            try:dependency=json.loads(receipt.read_text())
            except (OSError,ValueError):
                blocked=True;transient_dependencies.append(str(receipt));continue
            if not dependency.get('passed'):failed.append(str(receipt))
        if failed:
            finished[name]=dict(returncode=-1,failed_dependencies=failed,spec_sha256=digest);seen[name]=digest
            (out/'results'/(name+'.json')).write_text(json.dumps(finished[name],indent=2)+'\n');continue
        if not blocked:pending.append((name,spec,digest))
    memory={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    admissions=[]
    for name,spec,digest in pending:
        if len(active)==slots:break
        forecast=sum(s['forecast_gib'] for _,s in active.values())+spec['forecast_gib']
        required=(forecast*1.2+16)*1024**3
        decision=dict(name=name,available_bytes=memory['MemAvailable'],forecast_gib=forecast,required_bytes=required,admitted=memory['MemAvailable']>required)
        admissions.append(decision)
        if not decision['admitted']:continue
        selected_root=Path(spec.get('source_root',str(root))).resolve()
        assert selected_root.parent==root.resolve().parent and re.fullmatch(r'source-\d+',selected_root.name)
        source_manifest=selected_root/'source-manifest.json';assert source_manifest.is_file()
        script=selected_root/'project/experiments/control_v1'/spec['script'];assert script.is_file()
        cmd=['srun','--exclusive','-n1','-c16','--cpu-bind=cores','/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu',
             '--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1','--env','SLURM_JOB_ID='+job,image,'bash','-c',
             'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"','bash',str(script),*spec['args']]
        logs[name]=(out/(name+'.log')).open('w');active[name]=(subprocess.Popen(cmd,stdout=logs[name],stderr=subprocess.STDOUT),spec);seen[name]=digest
        (out/'commands'/(name+'.json')).write_text(json.dumps(dict(command=cmd,spec_sha256=digest,source_manifest_sha256=hashlib.sha256(source_manifest.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),admission=decision),indent=2)+'\n')
    all_names={p.stem for p in (out/'pending').glob('*.json')}
    state=out/'queue-state.json';temporary=out/'queue-state.tmp'
    temporary.write_text(json.dumps(dict(job=job,controller_pid=os.getpid(),slots=slots,cpus_per_slot=16,active=list(active),unfinished=sorted(all_names-set(active)-set(finished)),finished=finished,memory_admissions=admissions,waiting_for_complete_receipts=transient_dependencies,time=time.time()),indent=2)+'\n')
    os.replace(str(temporary),str(state))
    if (out/'queue-closed').exists() and not active and all_names==set(finished):break
    time.sleep(2)
(out/'queue-result.json').write_text(json.dumps(dict(passed=all(row['returncode']==0 for row in finished.values()),finished=finished),indent=2)+'\n')
