#!/bin/bash
#SBATCH --job-name=yzl-289-C-macroobs
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-macroobs-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
export C_OBS_RUN=$r/cu/runs/C-v20-native-clock4
export C_OBS_ODB=$C_OBS_RUN/global-candidate.odb
out=$r/audit/C-final-v1/macro-obs-v20
mkdir "$out"
cp "$r/audit/C-final-v1/"{macro-obs-export.tcl,macro-cut-coverage.py} "$out/"
sha256sum "$C_OBS_ODB" "$C_OBS_RUN/config.mk" "$out/"*.tcl "$out/"*.py > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit macro-obs-export.tcl > export.log 2>&1; klayout -b -r macro-cut-coverage.py > coverage.log 2>&1'
sha256sum "$C_OBS_ODB" "$C_OBS_RUN/config.mk" "$out/"*.tcl "$out/"*.py > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
