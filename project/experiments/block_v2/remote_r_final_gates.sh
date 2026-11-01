#!/bin/bash
#SBATCH --job-name=yzl-bv2-rfinalgates
#SBATCH --partition=c96
#SBATCH --cpus-per-task=96
#SBATCH --exclusive
#SBATCH --time=24:00:00
set -euo pipefail
test "$SLURM_CPUS_PER_TASK" -eq 96
root=$1
raw=$2
out=$3
native=$4
gds=$5
formal_forecast_gib=$6
function_computation=${7:-}
formal_computation=${8:-}
python3 - "$out.memory-admission.json" "$formal_forecast_gib" <<'PY'
import json,os,sys,time
from pathlib import Path
formal=int(sys.argv[2]);assert 192<=formal<=448
required=int((max(formal,3*64)*1.2+16)*1024**3)
observations=[]
while True:
 available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
 observations.append(dict(time_unix=time.time(),available_bytes=available,required_bytes=required))
 record=dict(passed=available>=required,job=os.environ['SLURM_JOB_ID'],exclusive_node=True,cpus=96,
  maximum_independent_ready_gates=4,formal_forecast_gib=formal,other_gate_forecast_gib=64,observations=observations,
  basis='Formal forecast supplied from actual completed139 native peak with margin; current139 observation222555616KiB already exceeds old192GiB forecast. Prior M final-function8088824KiB/187883cells scaled to R approx1.2M cells =>64GiB ordinary forecast. Weighted admission per running stage,20percent headroom and16GiB guard; six16CPU slots dynamically refill actual independent tasks. Memory can constrain concurrency below six.')
 Path(sys.argv[1]).write_text(json.dumps(record,indent=2)+'\n')
 if record['passed']:break
 time.sleep(30)
PY
extra=()
if test -n "$function_computation"; then extra+=(--r-function-computation "$function_computation"); fi
if test -n "$formal_computation"; then extra+=(--r-formal-computation "$formal_computation"); fi
exec bash "$root/project/experiments/block_v2/remote_gates.sh" "$root" "$raw" "$out" r \
 --r-native-computation "$native" --r-gds-computation "$gds" --r-formal-memory-gib "$formal_forecast_gib" \
 --memory-gib-per-worker 64 --memory-basis ExclusiveNode_weighted_per_stage_actual139_peak_formal_plus64GiB_ordinary20percent_headroom16GiB_guard "${extra[@]}"
