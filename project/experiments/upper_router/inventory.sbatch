#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-input
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
source_root=$task/source
kind=$(python3 -c 'import sys; print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
export TASK="$task" KIND="$kind"
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
root=Path(os.environ['TASK']); kind=os.environ['KIND']
data=json.loads((root/'source/work/YUZE-LU/230/inputs.json').read_text())
item=data['packages'][kind]
subprocess.run(['python3',str(root/'source/project/experiments/upper_router/stage_package.py'),
                item['archive'],item['sha256'],str(root/'packages'/kind)],check=True)
PY
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$source_root" \
  --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen,ROUTER_NATIVE_ODB=$task/packages/$kind/native/6_final.odb,ROUTER_INVENTORY_TSV=$task/$kind-inventory.tsv" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -threads 10 -exit project/experiments/upper_router/native_inventory.tcl'
python3 "$source_root/project/experiments/upper_router/native_inventory.py" --tsv "$task/$kind-inventory.tsv" "$task/packages/$kind" "$task/$kind-inventory.json"
