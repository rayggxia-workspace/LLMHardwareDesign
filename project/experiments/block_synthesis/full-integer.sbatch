#!/bin/bash
#SBATCH --job-name=yzl-syn-integer
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
sha256sum *.py *.cpp *.sbatch "$2" "$3" "$4" "$5" "$6"/*.hpp > input.sha256
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$6" native_reference.cpp -o native-reference > build.log 2>&1
options=()
if [[ -n "${7:-}" ]]; then options+=(--reference-nodes "$7");sha256sum "$7" >> input.sha256;fi
if [[ "${8:-}" == wide ]]; then options+=(--wide);fi
if [[ "${9:-}" == program-ir ]]; then options+=(--program-ir);fi
"$python" -u full_integer.py "${options[@]}" "$2" "$3" "$4" "$5" generated "${sim[@]}" "$root/native-reference" > integer.log 2>&1
sha256sum generated/* native-reference > output.sha256
