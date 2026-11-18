#!/bin/bash
#SBATCH --job-name=yzl-289-U-audit
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-independent-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/U-*) ;; *) exit 2;; esac
out=$root/audit/$(basename "$run")-independent-v2
mkdir "$out"
cp "$root/audit/u-formal.py" "$root/audit/u-control-proof.py" "$root/audit/u-final-evidence.tcl" "$root/audit/u-contract.py" "$out/"
sha256sum "$out/u-formal.py" "$out/u-control-proof.py" "$out/u-final-evidence.tcl" "$out/u-contract.py" > "$out/proof-scripts.sha256"
printf '%s\n' "$run" > "$out/source-run.txt"
cat > "$out/export.tcl" <<'TCL'
read_db /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base/4_cts.odb
write_verilog cts-baseline.v
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/rebase-evidence.tcl
rebase_evidence original
TCL
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit export.tcl > export.log 2>&1; export U_FINAL_RES=$(find "$2/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1); export U_LIBS=$(sed -n "s/^export ADDITIONAL_LIBS = //p" "$2/config.mk" | tail -1); openroad -no_init -exit u-final-evidence.tcl > final-evidence.log 2>&1; python3 "$3/u-contract.py" "$2" "$3"; python3 "$3/u-formal.py" "$2" "$3"; python3 "$3/u-control-proof.py" "$3"' _ "$root" "$run" "$out"
