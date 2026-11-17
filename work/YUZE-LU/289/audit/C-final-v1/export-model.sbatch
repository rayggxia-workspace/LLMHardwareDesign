#!/bin/bash
#SBATCH --job-name=yzl-289-C-model
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-model-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/C-*|"$root"/audit/C-*) ;; *) exit 2;; esac
out=$root/audit/C-final-v1/model-$(basename "$run")
mkdir "$out"
cp "$root/audit/C-final-v1/"{export-model.tcl,model-import.tcl,model-check.py,parent-coverage.py} "$out/"
cp "$root/audit/compare_lef.py" "$root/gs/leaf_cut_obs.py" "$out/"
cp "$root/cu/pack-cu-lef.py" "$out/pack.py"
python3 - "$out/pack.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();s=s.replace("Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/leaf_cut_obs.py')","Path(__file__).parent/'leaf_cut_obs.py'");p.write_text(s)
PY
export C_MODEL_DIR=$out
export C_FINAL_RES=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
export C_GDS=$C_FINAL_RES/6_final.gds
export C_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
printf '%s\n' "$run" > "$out/source-run.txt"
sha256sum "$C_FINAL_RES/6_final.odb" "$C_FINAL_RES/6_final.sdc" "$C_FINAL_RES/6_final.spef" "$C_FINAL_RES/6_final.gds" $C_LIBS "$out/"*.tcl "$out/"*.py > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit export-model.tcl > export.log 2>&1; openroad -no_init -exit model-import.tcl > import.log 2>&1; yosys -p "read_liberty -lib cfj_group_c_memory_legacy.lib; write_json imported-model.json" > yosys-import.log 2>&1; python3 model-check.py'
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; mkdir parent-abstract; python3 pack.py cfj_group_c_memory_legacy.lef "$C_GDS" parent-abstract/cfj_group_c_memory_legacy.lef; cp cfj_group_c_memory_legacy.lib model-import.tcl model-check.py parent-abstract/; cd parent-abstract; openroad -no_init -exit model-import.tcl > import.log 2>&1; yosys -p "read_liberty -lib cfj_group_c_memory_legacy.lib; write_json imported-model.json" > yosys.log 2>&1; python3 model-check.py; cd ..; klayout -b -r parent-coverage.py > parent-coverage.log 2>&1'
sha256sum "$C_FINAL_RES/6_final.odb" "$C_FINAL_RES/6_final.sdc" "$C_FINAL_RES/6_final.spef" "$C_FINAL_RES/6_final.gds" $C_LIBS "$out/"*.tcl "$out/"*.py > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
sha256sum "$out/cfj_group_c_memory_legacy.lib" "$out/cfj_group_c_memory_legacy.lef" > "$out/models.sha256"
