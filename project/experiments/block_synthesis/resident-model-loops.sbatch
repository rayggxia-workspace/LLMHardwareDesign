#!/bin/bash
#SBATCH --job-name=yzl-resident-loops
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
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
sha256sum *.py *.cpp *.sv "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}"/*.hpp > input.sha256
mkdir proof
tar -xzf "$5" -C proof
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"${10}" native_reference.cpp -o native-reference > build.log 2>&1
"$python" -u -B resident_model_loops.py "$2" "$3" "$4" proof "$6" "$7" "$8" "$9" generated "${sim[@]}" "$root/native-reference" > replay.log 2>&1
sha256sum generated/* tests.log replay.log native-reference > output.sha256
