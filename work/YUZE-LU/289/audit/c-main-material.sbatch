#!/bin/bash
#SBATCH --job-name=yzl-C-material
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-material-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$r/audit/C-main-clock4-physical-v1/rcx-material-$SLURM_JOB_ID
mkdir "$out"
sourcepath=$r/cu/diagnostics/C-main-v1-rcx
cp "$sourcepath/before-rcx.def" "$out/before.def"
cp "$sourcepath/after-rcx.def" "$out/after.def"
cp "$r/audit/C-final-v1/def-material.py" "$r/audit/C-final-v1/antenna-meta.tcl" "$out/"
export C_ANT_RES=$r/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base
export C_CANON_BASE=$out
export C_CANON_OUT=$out/material
sha256sum "$sourcepath/"{before-rcx.def,after-rcx.def,after-rcx.odb} "$C_ANT_RES/6_final.odb" "$out/"{def-material.py,antenna-meta.tcl} > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit antenna-meta.tcl > metadata.log 2>&1; klayout -b -r def-material.py > material.log 2>&1'
sha256sum "$sourcepath/"{before-rcx.def,after-rcx.def,after-rcx.odb} "$C_ANT_RES/6_final.odb" "$out/"{def-material.py,antenna-meta.tcl} > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
