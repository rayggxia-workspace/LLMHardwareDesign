#!/bin/bash
#SBATCH -J yzl-C-shared-area
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n6
#SBATCH -c8
#SBATCH -t 00:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-shared-area-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-cached-shared-diagnostic
mkdir "$out"
cp "$root/cu/loader-placement-diagnostic-v2.tcl" "$out/physical.tcl"
pids=()
for kind in A AB; do
 mkdir "$out/$kind-map"
 sed "s|$root/cu/loader-cached.sv|$root/audit/loader-cached-shared-$kind.sv|" "$root/cu/loader-fast3-cached/map.ys" > "$out/$kind-map/map.ys"
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out/$kind-map" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; yosys -s map.ys > map.log 2>&1' &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
pids=()
for kind in baseline A AB; do
 for util in 30 50; do
  run=$out/$kind-u$util;mkdir "$run"
  if [[ $kind == baseline ]]; then cp "$root/cu/loader-fast3-cached/mapped.v" "$run/mapped.v"; else cp "$out/$kind-map/mapped.v" "$run/mapped.v"; fi
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env "OMP_NUM_THREADS=8,UTIL=$util" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1" > physical.log 2>&1' _ "$out/physical.tcl" &
  pids+=("$!")
 done
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
