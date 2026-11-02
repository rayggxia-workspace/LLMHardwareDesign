"""Create explicit version-bound server source archive and reviewed deployment script."""
from pathlib import Path
import argparse,base64,hashlib,json,re,tarfile
P=Path(__file__).resolve().parent;R=P/'integrated';A=R/'work/Melodydt/151'
ap=argparse.ArgumentParser();ap.add_argument('--source-commit',required=True);ap.add_argument('--run',default='r01');a=ap.parse_args()
assert re.fullmatch('[0-9a-f]{40}',a.source_commit) and re.fullmatch('r[0-9]{2}',a.run)
task='/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af16-cd8dfc9-20261102';inputdir=task+'/input-'+a.run;outdir=task+'/runs/'+a.run
contract=json.loads((A/'af16-tb-contract.json').read_text(encoding='utf8'))
paths=set(contract['compile_sources'])|{'project/rtl/block_v2/block_v2_g_tables.svh','project/rtl/block_v2/block_v2_n_exp.svh'}
paths.update(contract.get('reference_dependencies',[]))
paths.update(contract.get('input_paths',[]))
paths.update('work/Melodydt/151/'+x for x in ['af16_integer_reference.py','build_af16_vectors.py','build_af16_tb.py','af16-contract-vectors.json','af16-tb-contract.json','run_af16_verilator.py','check_af16_oracle.py','af16-oracle-checks.json'])
manifest={'source_commit':a.source_commit,'input_parent':'cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6','files':[]}
for name in sorted(paths):
 raw=(R/name).read_bytes();manifest['files'].append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
m=P/('source-manifest-'+a.run+'.json');m.write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf8'))
archive=P/('server-source-'+a.run+'.tar.gz');assert not archive.exists()
with tarfile.open(str(archive),'w:gz') as t:
 for name in sorted(paths):t.add(str(R/name),arcname=name,recursive=False)
 t.add(str(m),arcname='source-manifest.json',recursive=False)
template='''#!/bin/bash
#SBATCH --job-name=zenanyan-af16
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=@TASK@/slurm/zenanyan-af16-%j.out
#SBATCH --error=@TASK@/slurm/zenanyan-af16-%j.err
set -euo pipefail
umask 077
test -n "${SLURM_JOB_ID:?allocation required}"
test "${SLURM_CPUS_PER_TASK:?allocation required}" -ge 8
TASK_BOOTSTRAP_DIR="$(mktemp -d @TASK@/runs/.bootstrap-XXXXXX)"
mkdir -p "$TASK_BOOTSTRAP_DIR/home" "$TASK_BOOTSTRAP_DIR/tmp" "$TASK_BOOTSTRAP_DIR/cache"
mkdir -p "$TASK_BOOTSTRAP_DIR/singularity-cache" "$TASK_BOOTSTRAP_DIR/singularity-tmp"
export SINGULARITY_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export SINGULARITY_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export APPTAINER_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export APPTAINER_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export TMPDIR="$TASK_BOOTSTRAP_DIR/tmp"
export XDG_CACHE_HOME="$TASK_BOOTSTRAP_DIR/cache"
TASK_IMAGE_SHA="$(sha256sum /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif | cut -d' ' -f1)"
printf "job=%s node=%s image_sha=%s source=@COMMIT@\\n" "$SLURM_JOB_ID" "${SLURMD_NODENAME:-unverified}" "$TASK_IMAGE_SHA"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --no-home --bind /public/home/yuzelu/Melodydt:/public/home/yuzelu/Melodydt:rw --bind /public/home/yuzelu/opt:/public/home/yuzelu/opt:ro --pwd @INPUT@ --home "$TASK_BOOTSTRAP_DIR/home" --bind "$TASK_BOOTSTRAP_DIR/tmp:/tmp:rw" --env "TMPDIR=$TASK_BOOTSTRAP_DIR/tmp,XDG_CACHE_HOME=$TASK_BOOTSTRAP_DIR/cache,OMP_NUM_THREADS=1" --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_JOB_NAME=$SLURM_JOB_NAME,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-},SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-}" /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif python3 @INPUT@/work/Melodydt/151/run_af16_verilator.py --root @INPUT@ --output @OUTPUT@ --source-commit @COMMIT@ --container-sha256 "$TASK_IMAGE_SHA"
'''
script=template.replace('@TASK@',task).replace('@INPUT@',inputdir).replace('@OUTPUT@',outdir).replace('@COMMIT@',a.source_commit)
(P/('submit-'+a.run+'.sbatch')).write_bytes(script.encode('utf8'))
raw=archive.read_bytes();archive_sha=hashlib.sha256(raw).hexdigest()
deploy='''from pathlib import Path
import base64,hashlib,io,json,subprocess,tarfile
task=Path(TASKVALUE);destination=Path(INPUTVALUE)
assert Path('/public/home/yuzelu/Melodydt') in task.resolve().parents
assert not destination.exists(),'refuse overwrite of existing input'
for part in ['slurm','runs']:(task/part).mkdir(parents=True,exist_ok=True)
raw=base64.b64decode(ARCHIVEVALUE);assert hashlib.sha256(raw).hexdigest()==SHAVALUE
destination.mkdir()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
 for member in t.getmembers():
  target=(destination/member.name).resolve()
  assert destination.resolve() in target.parents and member.isfile(),member.name
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(t.extractfile(member).read())
manifest=json.loads((destination/'source-manifest.json').read_text())
for x in manifest['files']:
 r=(destination/x['path']).read_bytes();assert len(r)==x['bytes'] and hashlib.sha256(r).hexdigest()==x['sha256'],x['path']
submission=task/SUBMITNAME;assert not submission.exists();submission.write_bytes(base64.b64decode(SCRIPTVALUE))
run=subprocess.run(['sbatch','--parsable',str(submission)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
receipt={'task_root':str(task),'input':str(destination),'submission_command':['sbatch','--parsable',str(submission)],'source_commit':manifest['source_commit'],'archive_sha256':SHAVALUE,'file_count':len(manifest['files']),'rc':run.returncode,'stdout':run.stdout,'stderr':run.stderr}
if run.returncode==0:
 job=run.stdout.strip().split(';')[0];assert job.isdigit()
 q=subprocess.run(['squeue','-h','-j',job,'-o','%i %j %T %C %M %R'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 receipt['job_id']=job;receipt['queue']=q.stdout
(task/DEPLOYNAME).write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps(receipt,indent=2));raise SystemExit(run.returncode)
'''
values={'TASKVALUE':repr(task),'INPUTVALUE':repr(inputdir),'ARCHIVEVALUE':repr(base64.b64encode(raw).decode()),'SHAVALUE':repr(archive_sha),'SUBMITNAME':repr('submit-'+a.run+'.sbatch'),'SCRIPTVALUE':repr(base64.b64encode(script.encode()).decode()),'DEPLOYNAME':repr('deploy-'+a.run+'.json')}
for key in sorted(values,key=len,reverse=True):deploy=deploy.replace(key,values[key])
(P/('deploy-'+a.run+'.py')).write_bytes(deploy.encode('utf8'))
print(json.dumps({'archive':str(archive),'bytes':len(raw),'sha256':archive_sha,'files':len(paths),'source_commit':a.source_commit,'run':a.run}))
