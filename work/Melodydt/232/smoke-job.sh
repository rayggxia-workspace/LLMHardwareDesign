#!/usr/bin/env bash
#SBATCH --job-name=mdt-mainaudit
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --ntasks=1
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
date -Is > started.txt
scontrol show job "$SLURM_JOB_ID" > allocation.txt
sha256sum /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif > image.sha256
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator --version > tools.txt
python3.12 --version >> tools.txt
sha256sum -c source.tar.sha256
python3.12 - <<'PY'
import json,hashlib
from pathlib import Path
for x in json.loads(Path('inputs.json').read_text())['source_files']:
    assert hashlib.sha256((Path('source')/x['path']).read_bytes()).hexdigest()==x['sha256'],x['path']
PY
bash "$root/source/project/experiments/pu_leaf_base/native_entry.sh" "$root" > native-entry.log 2>&1
python3.12 - <<'PY'
import json,hashlib,os,datetime
from pathlib import Path
p=Path('.');log=(p/'native-entry.log').read_text()
passed=log.count('PASS U native entry FMA counts 0..3, exact S reads, delayed ACK, invalid N/lane')
assert passed==3,passed
files=['inputs.json','source.tar.sha256','allocation.txt','image.sha256','tools.txt','native-entry.log','native-entry/compile.log','native-entry/endpoint.sv']
out={'passed':True,'executions':passed,'source_commit':'c4d7b960599b9d292f27eb4429d5f226a7156c95','job_id':os.environ['SLURM_JOB_ID'],'node':os.environ['SLURMD_NODENAME'],'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'U native entry smoke only; not an LLM or whole-system qualification','sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files}}
(p/'result.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS main audit smoke 3/3')
PY
