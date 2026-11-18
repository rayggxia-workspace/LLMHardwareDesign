#!/bin/bash
#SBATCH --job-name=yzl-289-U-pgphysical
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-pgphysical-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
src=$root/cu/runs/U-v15-guardant-f67-h3-u1.2
out=$root/audit/U-v15-pg-diagnostic
mkdir "$out"
cp "$src/config.mk" "$out/config.mk"
for kind in results logs reports objects; do mkdir -p "$out/flow/$kind/nangate45/u-overlay-current/base"; done
cp "$src/flow/results/nangate45/u-overlay-current/base/6_final.def" "$out/flow/results/nangate45/u-overlay-current/base/6_final.def"
printf '%s\n' 'DIAGNOSTIC ONLY: source failed PSM-0069. No physical/functional acceptance.' > "$out/NOT_ACCEPTED.txt"
sha256sum "$src/flow/results/nangate45/u-overlay-current/base/6_final.odb" "$src/flow/results/nangate45/u-overlay-current/base/6_final.def" "$out/config.mk" > "$out/source.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$PWD/config.mk" WORK_HOME="$PWD/flow" NUM_CORES=8 do-gds > gds.log 2>&1'
