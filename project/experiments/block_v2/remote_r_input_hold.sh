#!/bin/bash
#SBATCH --job-name=yzl-bv2-ringuard
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
set -euo pipefail
source_dir=$1
out=$2
native_source=$3
test "$SLURM_CPUS_PER_TASK" -eq 16
mkdir "$out"
python3 - "$native_source" "$out" <<'PY'
import json,shutil,sys
from pathlib import Path
source=Path(sys.argv[1]);out=Path(sys.argv[2]);path=source.parents[1]/'mapping/block_v1_r'
receipt=json.loads((path/'receipt.json').read_text());assert receipt['passed']
(out/'mapping').mkdir();shutil.copytree(path,out/'mapping/block_v1_r')
PY
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$source_dir" "$image" \
 /usr/bin/time -v bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_v2/resume_r_grt.py" --source "$3" --out "$2/pnr/r" --input-hold-guard' bash "$source_dir" "$out" "$native_source" > "$out/r-worker.log" 2>&1
