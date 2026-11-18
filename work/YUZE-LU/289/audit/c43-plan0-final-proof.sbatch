#!/bin/bash
#SBATCH -J yzl-C43-final-lec
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C43-plan0-final-proof-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C43-plan0-final-proof
mkdir "$out"
cp "$root/audit/c43-plan0-final-freeze.py" "$out/"
cp "$root/audit/c43-plan0-final-export.tcl" "$out/export.tcl"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit export.tcl > export.log 2>&1; python3 c43-plan0-final-freeze.py'
bash "$root/audit/c-final-v2.sbatch" "$out/source-manifest.json" "$out/proof"
