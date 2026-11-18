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
for kind in csa; do
 run=$root/loader-fast3-$kind
 mkdir -p "$run"
 test ! -e "$run/STARTED" || exit 2
 date -Is > "$run/STARTED"
 test -s "$root/loader-map-original/map.ys"
 sed "s@loader-original.sv@loader-$kind.sv@;s@abc -liberty@abc -script $root/fast-abc.script -liberty@" "$root/loader-map-original/map.ys" > "$run/map.ys"
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$run" --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
  set -euo pipefail
  source /OpenROAD-flow-scripts/env.sh
  yosys -s map.ys > synthesis.log 2>&1
  openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/loader-map-sta-v2.tcl > sta.log 2>&1
 '
done
