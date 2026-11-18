#!/bin/bash
#SBATCH -J yzl-289-loaderphys
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 2
#SBATCH -c 8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loaderphys-%j.log
set -uo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for kind in distributed-parallel; do
 for util in 30 50; do
  run=$root/loader-phys2-$kind-u$util
  mkdir -p "$run"
  test ! -e "$run/STARTED" || exit 2
  date -Is > "$run/STARTED"
  cp "$root/loader-fast3-$kind/mapped.v" "$run/mapped.v"
  srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env "OMP_NUM_THREADS=8,UTIL=$util" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loader-placement-diagnostic-v2.tcl > physical.log 2>&1' &
  pids+=("$!")
 done
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
