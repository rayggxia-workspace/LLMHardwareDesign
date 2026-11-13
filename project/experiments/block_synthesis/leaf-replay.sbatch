#!/bin/bash
#SBATCH --job-name=yzl-syn-replay
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
probe=$(realpath "$2")
sio=$(realpath "$3")
qualified=$(realpath "$4")
memory=$(realpath "$5")
reference=$(realpath "$6")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
for name in frozen-leaves/*; do cmp "$name" "$probe/inputs/${name##*/}"; done
sha256sum *.py *.cpp *.sv *.sbatch *.vlt frozen-leaves/* "$probe/input.sha256" "$sio/input.sha256" "$memory" > input.sha256
"$python" leaf_replay.py "$probe" "$sio" "$qualified" "$memory" "$root/generated" > generation.log 2>&1
"$python" leaf_report.py "$root/generated"
"$python" -m unittest discover -v -p 'test_*.py' > tests.log 2>&1
if [[ -n "${7:-}" ]]; then
 sha256sum "$7" >> input.sha256
 "$python" run.py "$7" generated/input-hardware.json full-audit --audit-only > full-audit.log 2>&1
fi
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
includes=(-Igenerated "-I$probe/inputs" "-I$probe/inputs/blocks" -isystem /public/home/yuzelu/opt/eda/verilator-5.042/share/verilator/include)
libs=()
for module in block_v2_m block_v2_g block_v2_n block_v2_e layer_dma; do includes+=("-I$reference/obj/$module");done
for module in block_v2_m block_v2_g block_v2_n; do libs+=("$reference/obj/$module/V${module}__ALL.a");done
for module in block_v2_e_compact r_stream_local transaction6k; do
 includes+=("-I$probe/obj/$module");libs+=("$probe/obj/$module/V${module}__ALL.a")
done
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror -DGENERATED_PLAN "${includes[@]}" native_probe.cpp \
 "${libs[@]}" "$reference/obj/layer_dma/libverilated.a" -pthread -latomic -o native-replay > link.log 2>&1
for initial in 0 1 2; do
 "${sim[@]}" ./native-replay +verilator+rand+reset+$initial > native-$initial.log 2>&1
 grep -q GENERATED_NATIVE_PLAN_PASS native-$initial.log
done
cmp native-0.log native-1.log
cmp native-0.log native-2.log
sha256sum native-*.log tests.log generated/* > output.sha256
