#!/bin/bash
#SBATCH --job-name=yzl-289-C-finalaudit
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-independent-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/C-*|"$root"/audit/C-*) ;; *) exit 2;; esac
out=$root/audit/C-final-v1/$(basename "$run")
mkdir "$out"
cp "$root/audit/C-final-v1/"{final-evidence.tcl,expected-contract.tcl,geometry-all.tcl,inputs.py,check.py} "$out/"
sha256sum "$out/"*.tcl "$out/"*.py > "$out/checker-scripts.sha256"
printf '%s\n' "$run" > "$out/source-run.txt"
cat > "$out/original.tcl" <<'TCL'
read_db /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb
source geometry-all.tcl
geometry_snapshot original-geometry.tsv
TCL
export C_FINAL_RES=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
export C_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 inputs.py "$1" "$PWD" before; openroad -no_init -exit original.tcl > original.log 2>&1; openroad -no_init -exit final-evidence.tcl > final-evidence.log 2>&1; openroad -no_init -exit expected-contract.tcl > expected-contract.log 2>&1; python3 check.py "$PWD" "$1"; python3 inputs.py "$1" "$PWD" after' _ "$run"
