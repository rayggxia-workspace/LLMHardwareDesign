#!/usr/bin/env bash
#SBATCH --job-name=yzl-flat-link
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;prepared=$2;root=$3;flat=$4
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;prepared=$2;root=$3;flat=$4
python3 project/experiments/upper_router/assembly_sta.py "$root/attempt17/base.json" "$root/attempt26/backend/bindings.json" "$flat/../configs.json" "$flat" "$task/sta"
python3 - "$task/sta/sta.tcl" "$task/link.tcl" <<"PY"
from pathlib import Path
import sys
raw=Path(sys.argv[1]).read_text().split("read_spef",1)[0]
Path(sys.argv[2]).write_text(raw+"puts ACTUAL_FLAT_LINK_AND_ORIGINAL_SDC_READ_PASS\n")
PY
openroad -no_init -threads 10 -exit "$task/link.tcl" > "$task/link.log" 2>&1
grep -q ACTUAL_FLAT_LINK_AND_ORIGINAL_SDC_READ_PASS "$task/link.log"
if grep -E "\[ERROR |STA-0366|STA-0450|STA-0471|STA-0432" "$task/link.log";then
 echo "invalid physical link or unresolved original SDC objects" >&2;exit 1
fi
' bash "$task" "$prepared" "$root" "$flat"
