#!/bin/bash
#SBATCH --job-name=yzl-bv2-rformal
#SBATCH --partition=c96
#SBATCH --cpus-per-task=80
#SBATCH --time=24:00:00
set -euo pipefail
root=$1
raw=$2
out=$3
function=$4
test "$SLURM_CPUS_PER_TASK" -eq 80
python3 - "$function" <<'PY'
import json,sys,time
from pathlib import Path
folder=Path(sys.argv[1]);deadline=time.monotonic()+8*3600
while True:
 p=folder/'physical-functional-proof.json'
 if p.exists():
  try:
   if json.loads(p.read_text())['passed']:break
  except (ValueError,KeyError):pass
 receipt=folder/'receipt.json'
 if receipt.exists():assert json.loads(receipt.read_text())['passed'],'Function computation failed before view became available'
 assert time.monotonic()<deadline,'Immutable physical function view not available within8h'
 time.sleep(20)
PY
# Together with the existing16CPU function job this reserves node26's CPU
# allocation to protect the mixed memory workload; the proof uses16CPU.
python3 - <<'PY'
import json
from pathlib import Path
available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
print(json.dumps(dict(passed=available>=384*1024**3,available_bytes=available,required_bytes=384*1024**3,
 formal_forecast_gib=288,function_forecast_gib=96,
 basis='Observed139 native peak223074104KiB;288GiB formal plus96GiB independent function with20percent headroom and16GiB guard totals476.8GiB. Reserve remaining80CPU allocation beside existing16CPU function to protect mixed workload RAM; proof uses16CPU.')))
assert available>=384*1024**3,available
PY
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$1/project/experiments/block_v2/qualify.py" formal-compute --source "$2" --out "$3" --function "$4"' bash "$root" "$raw" "$out" "$function"
