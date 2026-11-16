#!/bin/bash
#SBATCH --job-name=yzl-native-lane
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
ulimit -c 0
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
printf '%s\n' "${4:-8}" > frontier-width.txt
sha256sum source.tar native-lane.sbatch "$2" "$3" frontier-width.txt > input.sha256
"$python" -B -X faulthandler -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
"$python" -u -B -X faulthandler native_lane_survey.py "$2" "$3" generated --width "${4:-8}" > survey.log 2>&1
sha256sum generated/*.json tests.log survey.log > output.sha256
