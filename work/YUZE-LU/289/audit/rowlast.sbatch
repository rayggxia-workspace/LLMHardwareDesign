#!/bin/bash
#SBATCH -J yzl-289-rowlast
#SBATCH -p debug
#SBATCH -N 1
#SBATCH -n 2
#SBATCH -c 8
#SBATCH --time=00:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/rowlast-%j.log
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$base/audit/loader-fast-rowlast
mkdir -p "$run"
test ! -e "$run/STARTED"
date -Is > "$run/STARTED"
sed "s@$base/cu/loader-original.sv@$base/audit/loader-rowlast.sv@;s@abc -liberty@abc -script $base/cu/fast-abc.script -liberty@" "$base/cu/loader-map-original/map.ys" > "$run/map.ys"
srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; yosys -s map.ys > synthesis.log 2>&1'
pids=()
for util in 30 50; do
 dest=$base/audit/loader-phys-rowlast-u$util
 mkdir -p "$dest"
 cp "$run/mapped.v" "$dest/mapped.v"
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$dest" --env "OMP_NUM_THREADS=8,UTIL=$util" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loader-placement-diagnostic-v2.tcl > physical.log 2>&1' &
 pids+=("$!")
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
