#!/usr/bin/env python3
"""Stage exact source in a fresh personal directory and submit an UNLIMITED Slurm job."""
import argparse,ast,datetime,hashlib,json,shlex,subprocess,tarfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['probe','map','pnr','audit','gate'],required=True)
ap.add_argument('--commit',required=True);ap.add_argument('--reuse');ap.add_argument('--cpus',type=int,default=16)
args=ap.parse_args();root=Path(__file__).resolve().parents[3]
__import__('os').chdir(root)
assert len(args.commit)==40 and all(c in '0123456789abcdef'for c in args.commit)
assert 1<=args.cpus<=64
for p in(root/'project/experiments/dram_m_fifo').glob('*.py'):ast.parse(p.read_text())
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
remote='/public/home/yuzelu/PingyangHuang/issue-173-physical-'+args.mode+'-'+stamp
local=root/'.local'/('physical-'+args.mode+'-'+stamp);local.mkdir(parents=True,exist_ok=False)
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','yuzelu@10.129.166.172']
def call(code):
 p=subprocess.run(ssh+['python3 -B -I -S -c '+shlex.quote(code)],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return p.stdout.strip()
if args.reuse:
 print(call("from pathlib import Path; b=Path('/public/home/yuzelu/PingyangHuang').resolve(); p=Path("+repr(args.reuse)+"); assert p.is_dir() and not p.is_symlink() and p.resolve().parent==b;print('Verified read-only input: '+str(p))"))
print(call("from pathlib import Path; b=Path('/public/home/yuzelu/PingyangHuang').resolve(); p=Path("+repr(remote)+"); assert p.parent.resolve()==b and not p.exists();p.mkdir();print(p)"))
paths=[Path('project/rtl/block_v2/block_v2_m.sv'),
 *sorted(Path('project/rtl/dram_m_fifo').glob('*.sv')),
 *sorted(p for p in Path('project/experiments/dram_m_fifo').glob('*') if p.is_file())]
manifest={'source_commit':args.commit,'mode':args.mode,'reuse':args.reuse,
 'files':[{'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in paths]}
(local/'source-snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
cmd=('source /OpenROAD-flow-scripts/env.sh; '
 'python3 -B project/experiments/dram_m_fifo/physical.py --mode '+args.mode+
 ' --out '+shlex.quote(remote+'/output')+' --jobs '+str(args.cpus))
if args.reuse:cmd+=' --reuse '+shlex.quote(args.reuse)
if args.mode=='probe':
 cmd='source /OpenROAD-flow-scripts/env.sh; command -v yosys openroad klayout; openroad -exit project/experiments/dram_m_fifo/physical_probe.tcl'
job='#!/bin/bash\n#SBATCH --job-name=hpy-dm173-pnr\nset -euo pipefail\n'
job+='r='+shlex.quote(remote)+'\n'
job+='mkdir -p "$r/home" "$r/tmp" "$r/cache" "$r/container-tmp"\n'
job+='export SINGULARITY_TMPDIR="$r/container-tmp" SINGULARITY_CACHEDIR="$r/cache"\n'
job+='image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif\n'
job+='sha256sum "$image" > "$r/image.sha256"\n'
job+='test "$(cut -d " " -f 1 "$r/image.sha256")" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a\n'
# Conservative 64GiB P&R forecast, before launching compute.
job+="python3 -B -I -S -c "+shlex.quote("import json,pathlib;v={a.split(':')[0]:a.split(':')[1].strip() for a in pathlib.Path('/proc/meminfo').read_text().splitlines()};a=int(v['MemAvailable'].split()[0])*1024;print(json.dumps({'available_bytes':a,'forecast_gib':64,'headroom':1.2,'guard_gib':16}));assert a>(64*1.2+16)*1024**3")+" > \"$r/memory-admission.json\"\n"
binds=[remote]
if args.reuse:
 reuse=args.reuse
 assert reuse.startswith('/public/home/yuzelu/PingyangHuang/issue-173-')
 binds.append(reuse)
job+='srun --ntasks=1 --cpus-per-task='+str(args.cpus)+' --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --containall --home "$r/home" --bind "$r/tmp:/tmp" '
for b in binds:job+='--bind '+shlex.quote(b+':'+b+('' if b==remote else ':ro'))+' '
job+='--bind /public/home/yuzelu/opt/eda/verilator-5.042:/public/home/yuzelu/opt/eda/verilator-5.042:ro --pwd "$r/source" '
job+='--env TMPDIR=/tmp,XDG_CACHE_HOME="$r/cache",PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS='+str(args.cpus)+',OPENBLAS_NUM_THREADS=1,SLURM_JOB_ID="$SLURM_JOB_ID",SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" "$image" /usr/bin/time -v /bin/bash -c '+shlex.quote('set -euo pipefail; '+cmd)+'\n'
(local/'job.sh').write_text(job,encoding='utf-8',newline='\n')
archive=local/'source.tar.gz'
with tarfile.open(archive,'w:gz')as tf:
 for p in paths:tf.add(p,arcname=p.as_posix())
 tf.add(local/'source-snapshot.json',arcname='source-snapshot.json');tf.add(local/'job.sh',arcname='job.sh')
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=15',str(archive),'yuzelu@10.129.166.172:'+remote+'/source.tar.gz'],check=True)
code="""from pathlib import Path
import hashlib,tarfile,json
r=Path(REMOTE).resolve(); assert r.parent==Path('/public/home/yuzelu/PingyangHuang').resolve()
p=r/'source.tar.gz'; assert hashlib.sha256(p.read_bytes()).hexdigest()==SHA
o=r/'source';o.mkdir()
with tarfile.open(p)as tf:
 for m in tf.getmembers():assert m.isfile() and o in(o/m.name).resolve().parents
 tf.extractall(o)
v=json.loads((o/'source-snapshot.json').read_text())
for f in v['files']:
 b=(o/f['path']).read_bytes()
 assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
print(json.dumps({'checked':len(v['files']),'source_commit':v['source_commit']}))
""".replace('REMOTE',repr(remote)).replace('SHA',repr(digest))
print(call(code))
sb=['sbatch','--parsable','--partition=c64','--nodes=1','--ntasks=1','--cpus-per-task='+str(args.cpus),'--mem=0','--time=0',
 '--job-name=hpy-dm173-'+args.mode,'--chdir='+remote+'/source','--output='+remote+'/slurm-%j.out','--error='+remote+'/slurm-%j.err',remote+'/source/job.sh']
p=subprocess.run(ssh+[' '.join(shlex.quote(x)for x in sb)],capture_output=True,text=True)
if p.returncode:raise RuntimeError(p.stderr)
rec={'remote':remote,'job_id':p.stdout.strip().split(';')[0],'source_sha256':digest,'commit':args.commit,'sbatch':sb}
(local/'stage.json').write_text(json.dumps(rec,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(rec))

