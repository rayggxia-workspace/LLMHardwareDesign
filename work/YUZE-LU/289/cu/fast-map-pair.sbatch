#!/bin/bash
#SBATCH -J yzl-289-mapfast
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/fast-map-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
for kind in original parallel; do
 run=$root/loader-fast-$kind
 mkdir -p "$run"
 test ! -e "$run/STARTED" || exit 2
 date -Is > "$run/STARTED"
 test -s "$root/loader-map-$kind/map.ys"
 sed 's/abc -liberty/abc -fast -liberty/' "$root/loader-map-$kind/map.ys" > "$run/map.ys"
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
  set -euo pipefail
  source /OpenROAD-flow-scripts/env.sh
  yosys -s map.ys > synthesis.log 2>&1
  openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loader-map-sta.tcl > sta.log 2>&1
 '
done
