#!/bin/bash
#SBATCH --job-name=yzl-289-C-antmap
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antmap-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
export C_ANT_RUN=$(realpath "$1")
export C_ANT_REPORT=$(realpath "$2")
export C_ANT_BINDING=$(realpath "$3")
case "$C_ANT_RUN" in "$r"/cu/runs/C-*|"$r"/audit/C-*) ;; *) exit 2;; esac
export C_ANT_RES=$(find "$C_ANT_RUN/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
out=$r/audit/C-final-v1/antenna-$(basename "$C_ANT_RUN")-$SLURM_JOB_ID
mkdir "$out"
cp "$r/audit/C-final-v1/"{antenna-meta.tcl,antenna-map.py} "$out/"
printf '%s\n' "$C_ANT_RUN" > "$out/source-run.txt"
sha256sum "$C_ANT_RES/6_final.odb" "$C_ANT_RES/6_final.def" "$C_ANT_RES/6_final.gds" "$C_ANT_RUN/config.mk" "$C_ANT_REPORT" "$C_ANT_BINDING" "$out/"*.tcl "$out/"*.py > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit antenna-meta.tcl > metadata.log 2>&1; klayout -b -r antenna-map.py > mapping.log 2>&1'
sha256sum "$C_ANT_RES/6_final.odb" "$C_ANT_RES/6_final.def" "$C_ANT_RES/6_final.gds" "$C_ANT_RUN/config.mk" "$C_ANT_REPORT" "$C_ANT_BINDING" "$out/"*.tcl "$out/"*.py > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
