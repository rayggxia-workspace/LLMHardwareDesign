#!/usr/bin/env bash
# Reject known-invalid extracted timing/PG/electrical candidates before full DRC.
# Passing this check is NOT qualification: the original complete DRC still runs.
set -euo pipefail
run=$1
source_dir=$2
out="$run/$SLURM_ARRAY_TASK_ID"
result=$(find "$out/flow/results" -name 6_final.odb -printf '%h\n')
[[ -n "$result" && -s "$result/6_final.spef" ]]
export SINGULARITYENV_CFJ_FINAL_ODB="$result/6_final.odb"
export SINGULARITYENV_CFJ_OVERLAY_DIR="$out"
export SINGULARITYENV_CFJ_FINAL_LIBS
SINGULARITYENV_CFJ_FINAL_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$out/config.mk")
srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1/native_audit.tcl"' \
 bash "$source_dir" > "$out/native-precheck.log" 2>&1
python3.12 - "$out" <<'PY'
from pathlib import Path
import json
import sys

out = Path(sys.argv[1])
counts = dict(line.split() for line in (out / 'native-sta-counts.tsv').read_text().splitlines())
assert set(counts) == {'setup', 'hold', 'capacitance', 'slew', 'fanout'}
counts = {k: int(v) for k, v in counts.items()}
log = (out / 'native-precheck.log').read_text()
pg = all(f'All shapes on net {n} are connected.' in log for n in ('VDD', 'VSS'))
passed = pg and not any(counts.values())
receipt = dict(passed=passed, violations=counts, pg_connected=pg,
               qualification=False, full_original_drc_required=True)
(out / 'native-precheck.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt), flush=True)
assert passed, 'Reject extracted candidate before full DRC; original limits unchanged'
PY
