#!/bin/bash
#SBATCH --job-name=yzl-sc234-mpwr
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py *.cpp *.sv *.sbatch > input.sha256
"$python" -u capture_operands.py ../frozen220/project/experiments/block_synthesis /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-220-statecost-v2-plan/generated/five-groups-ir.json operands > capture.log 2>&1
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
    --env OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=10,MKL_NUM_THREADS=10,PYTHONDONTWRITEBYTECODE=1 \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    python3 -u m_activity.py > calibration.log 2>&1
    sha256sum m-calibration.json sample-*/receipt.json sample-*/power.log > output.sha256
    '
