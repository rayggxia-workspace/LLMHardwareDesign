#!/bin/bash
#SBATCH --job-name=yzl-nexp-contract
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
reference=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-38-final/inputs/blocks
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
vl=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
sha256sum *.py *.cpp frozen-n/* "$reference"/*.hpp > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
"$python" -B nexp_probe.py transcript > transcript.log 2>&1
"${sim[@]}" "$vl" --cc --exe --build -j "$SLURM_CPUS_PER_TASK" --assert --top-module block_v2_n \
 --Mdir "$root/obj" -I"$root/frozen-n" "$root/frozen-n/block_v2_n.sv" "$root/frozen-n/block_v2_n_group.sv" \
 "$root/nexp_probe.cpp" -CFLAGS "-std=c++17 -O2 -Wall -Wextra -Werror -I$reference" > build.log 2>&1
for initial in 0 1 2; do
 "${sim[@]}" ./obj/Vblock_v2_n transcript/commands.txt +verilator+rand+reset+$initial > "native-$initial.log" 2>&1
 grep -q NEXP_NATIVE_PASS "native-$initial.log"
done
cmp native-0.log native-1.log
cmp native-0.log native-2.log
set +e
"${sim[@]}" ./obj/Vblock_v2_n transcript/old-count-one.txt > negative.log 2>&1
negative=$?
set -e
test "$negative" = 3
grep -q NEXP_SEMANTIC_MISMATCH negative.log
sha256sum tests.log native-*.log negative.log transcript/* input.sha256 > output.sha256
