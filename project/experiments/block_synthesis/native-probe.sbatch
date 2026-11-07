#!/bin/bash
#SBATCH --job-name=yzl-syn-leaves
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
reference=$(realpath "$2")
qualified=$(realpath "$3")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
mkdir inputs obj tmp
cp -a "$reference/source/include/blocks" inputs/blocks
cp "$reference/native_engines.hpp" "$reference/native_memory.hpp" inputs/
cp frozen-leaves/* inputs/
mkdir inputs/r_local_state
cp frozen-leaves/r_stream_local.sv frozen-leaves/r_state_store.sv inputs/r_local_state/
cmp frozen-leaves/block_v2_m.sv "$reference/rtl/project/rtl/block_v2/block_v2_m.sv"
cmp frozen-leaves/block_v2_g.sv "$reference/rtl/project/rtl/block_v2/block_v2_g.sv"
cmp frozen-leaves/block_v2_e.sv "$qualified/source/project/rtl/block_v2/block_v2_e.sv"
cmp "$qualified/source/project/rtl/block_v2/block_v2_n.sv" "$reference/rtl/project/rtl/block_v2/block_v2_n.sv"
sha256sum *.py *.cpp inputs/*.sv inputs/*.hpp inputs/blocks/*.hpp \
 native_t_lint.vlt "$reference/rtl/project/experiments/control_v1/native_r_lint.vlt" \
 "$reference/obj/block_v2_m/Vblock_v2_m__ALL.a" "$reference/obj/block_v2_g/Vblock_v2_g__ALL.a" \
 "$reference/obj/block_v2_n/Vblock_v2_n__ALL.a" > input.sha256
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/tmp"
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
vl=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for module in block_v2_e_compact r_stream_local transaction6k; do
 case "$module" in
  block_v2_e_compact) files=(inputs/block_v2_e.sv inputs/block_v2_e_compact.sv);;
  r_stream_local) files=(inputs/r_local_state/r_stream_local.sv inputs/r_local_state/r_state_store.sv "$reference/rtl/project/experiments/control_v1/native_r_lint.vlt");;
  transaction6k) files=(inputs/transaction6k.sv "$root/native_t_lint.vlt");;
 esac
 "${sim[@]}" "$vl" --cc --build -j "$SLURM_CPUS_PER_TASK" --assert --top-module "$module" --Mdir "$root/obj/$module" "${files[@]}" > "build-$module.log" 2>&1
done
includes=(-Iinputs -Iinputs/blocks -isystem /public/home/yuzelu/opt/eda/verilator-5.042/share/verilator/include)
libs=()
for module in block_v2_m block_v2_g block_v2_n block_v2_e layer_dma; do
 includes+=("-I$reference/obj/$module")
done
for module in block_v2_m block_v2_g block_v2_n; do libs+=("$reference/obj/$module/V${module}__ALL.a");done
for module in block_v2_e_compact r_stream_local transaction6k; do
 includes+=("-I$root/obj/$module");libs+=("$root/obj/$module/V${module}__ALL.a")
done
"${sim[@]}" g++ -std=c++17 -O2 -Wall -Wextra -Werror "${includes[@]}" native_probe.cpp "${libs[@]}" \
 "$reference/obj/layer_dma/libverilated.a" -pthread -latomic -o native-probe > link.log 2>&1
for initial in 0 1 2; do
 "${sim[@]}" ./native-probe +verilator+rand+reset+$initial > "native-$initial.log" 2>&1
 grep -q NATIVE_LEAF_PROBE_PASS "native-$initial.log"
done
cmp native-0.log native-1.log
cmp native-0.log native-2.log
sha256sum native-*.log native-probe > output.sha256
