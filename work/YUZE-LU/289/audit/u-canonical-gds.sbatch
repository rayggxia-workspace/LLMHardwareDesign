#!/bin/bash
#SBATCH --job-name=yzl-289-canonical-gds
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/canonical-gds-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$r/audit/U-antenna/candidate-U-v18-canonical
mkdir "$out"
cp "$r/audit/U-v15-pg-diagnostic/config.mk" "$out/config.mk"
for k in results logs reports objects; do mkdir -p "$out/flow/$k/nangate45/u-overlay-current/base"; done
cp "$r/audit/U-canonical-all-v1/canonical.def" "$out/flow/results/nangate45/u-overlay-current/base/6_final.def"
echo 'PENDING: canonical afterRCX streamout diagnostic, not accepted' > "$out/PENDING.txt"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$PWD/config.mk" WORK_HOME="$PWD/flow" NUM_CORES=8 do-gds > gds.log 2>&1; bash "$1/audit/u-focused.sh" "$PWD"' _ "$r"
