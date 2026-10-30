#!/bin/bash
#SBATCH --job-name=hpy-p126-OBSapi
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
outdir="$PWD/obs_union_api/$1"
test ! -e "$outdir"
mkdir -p "$outdir"
export PINXY_OBS_PROBE_OUT="$outdir"
export TMPDIR=$PWD/tmp SINGULARITY_CACHEDIR=$PWD/cache SINGULARITY_TMPDIR=$PWD/tmp PYTHONDONTWRITEBYTECODE=1
singularity exec --cleanenv --home "$PWD/home" --pwd "$outdir" --env PINXY_OBS_PROBE_OUT="$outdir",SLURM_JOB_ID="$SLURM_JOB_ID" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif klayout -b -r "$PINXY_DRIVER_DIR/probe_obs_union_api.py" > "$outdir/native.log" 2>&1
python3 - "$outdir" <<'PY'
import json,sys,hashlib
from pathlib import Path
out=Path(sys.argv[1]);p=out/'execution.json';q=json.loads(p.read_text())
q['files']={f.name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in out.iterdir() if f.is_file() and f.name!='execution.json'}
p.write_text(json.dumps(q,indent=2)+'\n')
sys.exit(0 if not q.get('actual_failure') and q.get('exact_integer_XOR_empty') else 1)
PY
