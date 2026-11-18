#!/bin/bash
#SBATCH -J yzl-289-C-synthproof
#SBATCH -p c96,c64
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-synthproof-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/cu/runs/$1
old=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v
gate=$run/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v
test -s "$gate"
out=$root/audit/$1-synthproof
mkdir "$out"
cp "$root/audit/c-formal.py" "$root/audit/c-control-proof.py" "$out/"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 c-formal.py "$1" "$2" "$3" "$4"; python3 c-control-proof.py "$2"' _ "$run" "$out" "$old" "$gate"
