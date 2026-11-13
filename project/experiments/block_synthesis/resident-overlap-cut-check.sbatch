#!/bin/bash
#SBATCH --job-name=yzl-overlap-cut
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
sha256sum *.py *.cpp *.sv "$2" "$3" "$4" > input.sha256
mkdir old-source
tar -xf "$4" -C old-source
"$python" -B -X faulthandler -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
set +e
"$python" -u -B -X faulthandler old-source/resident_overlap_survey.py "$2" generated-old --mode dp --width 8 --wire-budget 18 --backbone "$3" > old-survey.log 2>&1
old_rc=$?
set -e
printf '%s\n' "$old_rc" > old.exit
"$python" -u -B -X faulthandler resident_overlap_survey.py "$2" generated-new --mode dp --width 8 --wire-budget 18 --backbone "$3" > new-survey.log 2>&1
"$python" -u -B -X faulthandler resident_overlap_survey.py "$2" generated-greedy --mode greedy --width 8 --wire-budget 18 --backbone "$3" > greedy-survey.log 2>&1
sha256sum generated-*/*.json tests.log *survey.log old.exit > output.sha256
