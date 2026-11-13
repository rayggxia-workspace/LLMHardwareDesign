#!/bin/bash
#SBATCH --job-name=yzl-syn-env
#SBATCH --partition=c64
#SBATCH --cpus-per-task=2
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
mkdir -p "$root/deps"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$python" -m pip install --disable-pip-version-check --no-index --find-links "$2" --target "$root/deps" 'ortools==9.10.4067' 'numpy==1.26.4' 'pandas==2.2.3' 'protobuf==5.29.5' > "$root/pip.log" 2>&1
PYTHONPATH="$root/deps" "$python" -c 'import ortools; from ortools.sat.python import cp_model; print(ortools.__version__); m=cp_model.CpModel(); x=m.new_int_var(1,3,"x"); m.minimize(x); s=cp_model.CpSolver(); print(s.status_name(s.solve(m)),s.value(x))' > "$root/environment.log"
"$python" -m pip freeze > "$root/base-python.txt"
sha256sum "$root/environment.log" "$root/pip.log" > "$root/environment.sha256"
