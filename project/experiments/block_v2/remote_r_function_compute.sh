#!/bin/bash
#SBATCH --job-name=yzl-bv2-rfunction
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
set -euo pipefail
root=$1
raw=$2
out=$3
organization=${4:-default}
case "$organization" in
 default) test "$SLURM_CPUS_PER_TASK" -eq 16; guard_gib=96; extra=();;
 ungrouped) test "$SLURM_CPUS_PER_TASK" -eq 80; guard_gib=192; extra=(--ungrouped);;
 *) exit 2;;
esac
mkdir -p "$(dirname "$out")"
python3 - "$guard_gib" "$(dirname "$out")/function-memory-admission.json" <<'PY'
import json,sys
from pathlib import Path
available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
required=int(sys.argv[1])*1024**3
assert available>=required,available
Path(sys.argv[2]).write_text(json.dumps(dict(passed=True,available_bytes=available,required_bytes=required))+'\n')
PY
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; root=$1; raw=$2; out=$3; shift 3; exec python3 "$root/project/experiments/block_v2/qualify.py" function-compute --source "$raw" --out "$out" "$@"' bash "$root" "$raw" "$out" "${extra[@]}"
