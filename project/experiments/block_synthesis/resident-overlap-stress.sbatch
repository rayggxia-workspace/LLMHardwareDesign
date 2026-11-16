#!/bin/bash
#SBATCH --job-name=yzl-overlap-stress
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
ulimit -c 0
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py "$2" "$3" > input.sha256
# This path is an immutable copy of the exact stress driver which failed on
# the local host. Only this job's frozen scheduler/checker is imported.
cp "$3" stress_overlap.py
PYTHONMALLOC=debug "$python" -u -B -X faulthandler stress_overlap.py "$2" stress-result.json --repeats 12 > stress.log 2>&1
sha256sum stress-result.json stress.log stress_overlap.py > output.sha256
