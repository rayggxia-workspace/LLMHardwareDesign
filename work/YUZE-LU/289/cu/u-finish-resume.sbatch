#!/bin/bash
#SBATCH -J yzl-289-U-final
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=08:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-final-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/runs/U-v7-macropdn-x8-seed0
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base
res=$run/flow/results/nangate45/u-overlay-current/base
test -s "$src/1_synth_lec.v"
cp "$src/1_synth_lec.v" "$res/1_synth_lec.v"
sha256sum "$src/1_synth_lec.v" "$res/1_synth_lec.v" > "$run/synth-lec-source-hashes.txt"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/runs/U-v7-macropdn-x8-seed0
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" do-finish > "$run/finish-resume.log" 2>&1
make "${args[@]}" do-gds > "$run/gds.log" 2>&1
a=0; bash "$root/signoff-v4.sh" "$run" || a=$?
b=0; bash "$root/lec-v3.sh" "$run" /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base/4_cts.odb || b=$?
test "$a" -eq 0 -a "$b" -eq 0
'
