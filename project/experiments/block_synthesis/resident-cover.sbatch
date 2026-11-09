#!/bin/bash
#SBATCH --job-name=yzl-resident-cover
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py *.cpp *.sv "$2" "$3" > input.sha256
mkdir proof
tar -xzf "$3" -C proof
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
args=("$2" proof generated --width 8 --wire-budget 18)
if [ "$#" -ge 4 ]; then sha256sum "$4" >> input.sha256; args+=(--backbone "$4"); fi
"$python" -u -B resident_cover_survey.py "${args[@]}" > survey.log 2>&1
sha256sum generated/* tests.log survey.log > output.sha256
