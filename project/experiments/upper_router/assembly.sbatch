#!/usr/bin/env bash
#SBATCH --job-name=yzl-nine-route
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;root=$2;r=project/experiments/upper_router
export ROUTER_ASSEMBLY_BASE=$root/attempt17/base.json ROUTER_ASSEMBLY_OUT=$task/native
klayout -b -r "$r/assemble_gds.py" > "$task/native-assembly.log" 2>&1
export PYTHONPATH=$PWD/$r
python3 - "$task" "$root" <<"PY"
import json,sys
from pathlib import Path
from resource_base import load_library
from assembly_case import make_assembly
task,root=map(Path,sys.argv[1:])
library=load_library(root/"attempt17/library.json")
for name,item in library.items():item["inventory_path"]=str(root/"attempt02"/(name+"-inventory.json"))
base=json.loads((root/"attempt17/base.json").read_text())
spec=make_assembly(base,library,root/"attempt01/packages",Path("project/experiments/block_v1/technology-2um-v1.json"),task/"native/native.gds")
(task/"spec.json").write_text(json.dumps(spec,indent=2)+"\n")
PY
python3 "$r/run.py" "$task/spec.json" "$task/routes.json" --rounds 8
python3 "$r/backend.py" "$task/spec.json" "$task/routes.json" "$task/backend" --dbu-per-micron 2000 --via-resistance-ohm .08
out=$task/backend
python3 project/experiments/block_v1/overlay.py /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef project/experiments/block_v1/technology-2um-v1.json "$out/technology"
export ROUTER_HANDOFF=$out ROUTER_NATIVE_GDS=$task/native/native.gds ROUTER_WIRE_WIDTH=4000
openroad -no_init -threads 10 -exit "$r/ingest.tcl" > "$out/ingest.log" 2>&1
klayout -b -r "$r/physical_readback.py" > "$out/physical-readback.log" 2>&1
' bash "$task" "$root"
