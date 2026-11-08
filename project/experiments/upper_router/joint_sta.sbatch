#!/usr/bin/env bash
#SBATCH --job-name=yzl-joint-sta
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2;flat=$3;scene=$4;field=$5;graph=$6
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;root=$2;flat=$3;scene=$4;field=$5;graph=$6;r=project/experiments/upper_router
python3 "$r/assemble_spef.py" "$root/attempt17/base.json" "$root/attempt17/library.json" "$root/attempt26/backend/bindings.json" "$task/native.spef"
python3 "$r/assembly_sta.py" "$root/attempt17/base.json" "$root/attempt26/backend/bindings.json" "$flat/../configs.json" "$flat" "$task/sta"
out=$task/sta
for projection in distributed driver farthest_sink;do
 for scale in 0 1 2;do
  name=$projection-coupling-$scale
  python3 "$r/stitch_rc.py" "$task/native.spef" "$root/attempt26/backend/bindings.json" "$graph" "$scene/scene.json" "$field/rows.jsonl" "$out/$name.spef" --node-projection "$projection" --coupling-scale "$scale"
  export ROUTER_STITCHED_SPEF=$out/$name.spef ROUTER_STA_STEM=$out/$name
  openroad -no_init -threads 10 -exit "$out/sta.tcl" > "$out/$name.log" 2>&1
 done
done
python3 "$r/timing_receipt.py" "$out"
' bash "$task" "$root" "$flat" "$scene" "$field" "$graph"
