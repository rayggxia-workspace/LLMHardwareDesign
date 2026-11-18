#!/bin/bash
#SBATCH --job-name=yzl-289-U-model
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-model-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/U-*|"$root"/audit/U-antenna/candidate-*|"$root"/u-physical/candidate-*|"$root"/audit/U-v15-pg-diagnostic) ;; *) exit 2;; esac
out=$root/audit/model-$(basename "$run")
mkdir "$out"
export U_FINAL_RES=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
cp "$root/audit/u-export-final.tcl" "$root/audit/u-model-import.tcl" "$root/audit/u-model-check.py" "$out/"
sha256sum "$U_FINAL_RES/6_final.odb" "$U_FINAL_RES/6_final.sdc" "$U_FINAL_RES/6_final.spef" $U_LIBS "$out/u-export-final.tcl" "$out/u-model-import.tcl" "$out/u-model-check.py" > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit u-export-final.tcl; openroad -no_init -exit u-model-import.tcl > model-import.log 2>&1; yosys -p "read_liberty -lib u_n32_controlled_dma_64.lib; write_json imported-model.json" > model-yosys-import.log 2>&1; python3 u-model-check.py' > "$out/export.log" 2>&1
sha256sum "$U_FINAL_RES/6_final.odb" "$U_FINAL_RES/6_final.sdc" "$U_FINAL_RES/6_final.spef" $U_LIBS "$out/u-export-final.tcl" "$out/u-model-import.tcl" "$out/u-model-check.py" > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
sha256sum "$out/u_n32_controlled_dma_64.lib" "$out/u_n32_controlled_dma_64.lef" > "$out/models.sha256"
