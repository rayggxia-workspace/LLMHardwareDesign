#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-phys
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
inputs=$2
source_root=$task/source
kind=$(python3 -c 'import sys; print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
mkdir "$task/$kind"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$source_root" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1; inputs=$2; kind=$3; native=$4
r=project/experiments/upper_router
stack=project/experiments/block_v1/technology-2um-v1.json
python3 "$r/fixture_case.py" "$native" "$inputs/$kind-inventory.json" "$stack" "$task/$kind/spec.json"
python3 "$r/run.py" "$task/$kind/spec.json" "$task/$kind/routes.json" --rounds 8
python3 "$r/backend.py" "$task/$kind/spec.json" "$task/$kind/routes.json" "$task/$kind/backend" --dbu-per-micron 2000 --via-resistance-ohm 0.08
out=$task/$kind/backend
python3 project/experiments/block_v1/overlay.py /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef "$stack" "$out/technology"
export ROUTER_HANDOFF=$out ROUTER_NATIVE_GDS=$native/native/6_final.gds ROUTER_WIRE_WIDTH=4000
openroad -no_init -threads 10 -exit "$r/ingest.tcl" > "$out/ingest.log" 2>&1
export PYTHONPATH=$PWD/$r
klayout -b -r "$r/physical_readback.py" > "$out/physical-readback.log" 2>&1
' bash "$task" "$inputs" "$kind" "$(dirname "$inputs")/attempt01/packages/$kind"
