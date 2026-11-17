#!/bin/bash
#SBATCH -J yzl-289-C-observer-binding
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-observer-binding-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/cu/runs/C-v16-genericadder-cached
old=$root/audit/C-v16-synth-replay/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v
gate=$run/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v
test -s "$gate"
out=$root/audit/C-observer-to-actual-binding
mkdir "$out"
cp "$root/audit/c-formal.py" "$root/audit/c-control-tags.py" "$out/"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 c-formal.py "$1" "$2" "$3" "$4"; python3 c-control-tags.py "$2"' _ "$run" "$out" "$old" "$gate"
