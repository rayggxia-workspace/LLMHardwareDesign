#!/bin/bash
#SBATCH -J yzl-C-v35-lec
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-i8h100-pmid200-proof-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/cu/runs/C-v35-unified-i8-h100-pmid200
out=$root/audit/C-v35-i8h100-pmid200-legalized-proof
mkdir "$out"
mkdir -p "$out/model-run/flow/results/nangate45/c-overlay-current/base"
cp "$run/config.mk" "$out/model-run/config.mk"
cp "$root/cu/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$out/gold.v"
cp "$run/legalized.v" "$out/gate.v"
cp "$root/audit/c-formal.py" "$root/audit/c-control-packed-v3.py" "$root/audit/c-v35-proof-binding.py" "$out/"
python3 "$out/c-v35-proof-binding.py" "$out" before
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 c-formal.py "$1/model-run" "$1" "$1/gold.v" "$1/gate.v"; python3 c-control-packed-v3.py "$1"' _ "$out"
python3 "$out/c-v35-proof-binding.py" "$out" after
