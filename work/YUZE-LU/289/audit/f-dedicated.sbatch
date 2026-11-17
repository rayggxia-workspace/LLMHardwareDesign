#!/bin/bash
#SBATCH --job-name=yzl-289-F-close
#SBATCH --partition=c96,c64,debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/F-dedicated-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
src=$root/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair3
python3 "$root/audit/prepare_notch.py" "$src"
c=$src-notch
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$c" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit repair.tcl' > "$c/implementation.log" 2>&1
# Allocation-owned dispatcher: later tasks are numbered executable shell files.
mkdir -p "$root/audit/f-queue"
while [[ ! -f "$root/audit/f-queue/STOP" ]]; do
 for task in "$root"/audit/f-queue/*.sh; do
  [[ -f "$task" && ! -f "$task.done" ]] || continue
  rc=0
  bash "$task" > "$task.log" 2>&1 || rc=$?
  printf '%s\n' "$rc" > "$task.done"
 done
 sleep 10
done
