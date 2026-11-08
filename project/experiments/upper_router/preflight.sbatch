#!/usr/bin/env bash
#SBATCH --job-name=yzl-flat-preflight
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2;flat=$3
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
task=$1;root=$2;flat=$3;r=project/experiments/upper_router
python3 "$r/assembly_sta.py" "$root/attempt17/base.json" "$root/attempt26/backend/bindings.json" "$flat/../configs.json" "$flat" "$task/sta"
python3 "$r/assemble_spef.py" "$root/attempt17/base.json" "$root/attempt17/library.json" "$root/attempt26/backend/bindings.json" "$task/native.spef"
python3 - "$task" /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-112-reuse-fast-plan/generated/nine-groups-count-experiment-ir.json <<"PY"
import json,sys
from pathlib import Path
ir=json.loads(Path(sys.argv[2]).read_text());h=ir["hardware"]
services={k:v for k,v in h["services"].items() if k.startswith(("P0.","U0.","C0."))}
nets={k:v for k,v in h["nets"].items() if k.startswith(("P0.","U0.","C0."))}
Path(sys.argv[1],"service-semantics.json").write_text(json.dumps({"services":services,"nets":nets},indent=2)+"\n")
PY
' bash "$task" "$root" "$flat"
