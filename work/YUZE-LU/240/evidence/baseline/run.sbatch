#!/bin/bash
#SBATCH --job-name=yzl-side-token
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=0
set -euo pipefail
cd "$1"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
prefix=/public/home/yuzelu/opt/systemc-3.0.2-issue219
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
sha256sum prepare.py replay.cpp run.sbatch "$prefix/lib/libsystemc.so" > source.sha256
"$python" -B prepare.py /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-277-phased-tile-full > prepare.log 2>&1
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror replay.cpp -I"$prefix/include" -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lsystemc -o replay > build.log 2>&1
"${sim[@]}" ./replay generated/tasks.txt > replay.log 2>&1
sha256sum generated/* prepare.log build.log replay.log > output.sha256
