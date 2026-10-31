#!/bin/bash
#SBATCH --job-name=yzl-bv2-rgates
#SBATCH --partition=c96
#SBATCH --cpus-per-task=96
#SBATCH --time=12:00:00
set -euo pipefail
test "$SLURM_CPUS_PER_TASK" -eq 96
root=$1
raw=$2
out=$3
python3 - "$out.memory-admission.json" <<'PY'
import json,os,sys
from pathlib import Path
values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
required=(320*1.2+16)*1024**3
record=dict(job=os.environ['SLURM_JOB_ID'],exclusive_node=True,cpus=96,maximum_independent_ready_gates=3,
    available_bytes=values['MemAvailable'],required_bytes=int(required),formal_forecast_gib=192,other_gate_forecast_gib=64,
    basis='Original R final native proof actual peak146771828KiB; reserve192GiB for formal plus two64GiB ordinary workers,20percent headroom and16GiB guard. Two such mixed gate groups could exceed512GiB, hence one exclusive node. Three actual ready gates remain parallel; later formal depends on function.',
    queue_uniform64_is_only_ordinary_slot_estimate_not_formal_bound=True)
Path(sys.argv[1]).write_text(json.dumps(record,indent=2)+'\n');assert values['MemAvailable']>=required,record
PY
exec bash "$root/project/experiments/block_v2/remote_gates.sh" "$root" "$raw" "$out" r --memory-gib-per-worker 64 --memory-basis ExclusiveNode400GiB_admission_formal192_other2x64_actualR146771828KiB_threeReadyStages
