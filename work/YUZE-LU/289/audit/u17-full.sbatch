#!/bin/bash
#SBATCH --job-name=yzl-289-U17-full
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U17-full-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$r/audit/U-antenna/candidate-U-v17-postrcx
res=$run/flow/results/nangate45/u-overlay-current/base
cmp "$r/u-physical/rcx-def-uncached-119810/original/after.def" "$res/6_final.def"
cp "$r/u-physical/rcx-def-uncached-119810/original/after.odb" "$res/6_final.odb"
printf 'read_db %s\nwrite_verilog %s\n' "$res/6_final.odb" "$res/6_final.v" > "$run/export-v.tcl"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$1/export-v.tcl" > "$1/export-v.log" 2>&1; bash "$2/audit/u-full.sh" "$1"' _ "$run" "$r"
