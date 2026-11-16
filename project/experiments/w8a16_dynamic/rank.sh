#!/usr/bin/env bash
set -euo pipefail
root=$1
seed=$2
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$python" -B "$root/source/project/experiments/w8a16_dynamic/oracle.py" \
 --seed "$seed" --out "$root/seed-$seed/oracle.json"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" \
 "$image" python3 -B "$root/source/project/experiments/w8a16_dynamic/check.py" \
 --source "$root/source" --out "$root/rtl-$seed" --seed "$seed" \
 --checkpoint "$root/checkpoint/checkpoint-vectors.json" \
 --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
