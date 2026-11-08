#!/bin/bash
# Lightweight one-core candidate RTL test; this is not a physical flow.
set -euo pipefail
repo=$(realpath "$1"); out=$2; operand=$(realpath "$3"); baseline=$(realpath "$4")
: "${VERILATOR_ROOT:?set the qualified Verilator root}"
mkdir "$out";out=$(realpath "$out")
cp "$repo/project/experiments/m_streaming/rtl/block_v2_m.sv" "$out/"
cp "$repo/project/experiments/m_streaming/longk_probe.cpp" "$out/"
cp "$repo/project/experiments/systemc_benchmark/"{m_activity.cpp,m_profile.cpp} "$out/"
cp "$operand" "$out/m-tile-0.tsv"
verilator --version >"$out/tools.log"
g++ --version >>"$out/tools.log"
verilator --lint-only --top-module block_v2_m "$out/block_v2_m.sv" >"$out/lint.log" 2>&1
verilator --cc --exe --build -j 1 --trace --x-initial unique --x-assign unique \
 --top-module block_v2_m -Mdir "$out/obj" -CFLAGS '-O1' \
 "$out/block_v2_m.sv" "$out/longk_probe.cpp" -o longk-probe >"$out/build.log" 2>&1
c="$out/obj";inc="$VERILATOR_ROOT/include"
g++ -std=c++17 -O1 -DVM_TRACE=1 -DVM_TRACE_VCD=1 -DVM_TRACE_FST=0 \
 -DVM_TRACE_SAIF=0 -DVM_TIMING=0 -DVM_COVERAGE=0 -I"$c" -I"$inc" -I"$inc/vltstd" \
 "$out/m_profile.cpp" "$c/Vblock_v2_m__ALL.a" "$c/verilated.o" \
 "$c/verilated_vcd_c.o" "$c/verilated_threads.o" -pthread -latomic \
 -o "$out/legacy-profile" >"$out/build-profile.log" 2>&1
for pair in '1 143' '2 143' '2 144';do
 read init seed <<< "$pair"
 "$out/obj/longk-probe" +verilator+rand+reset+$init +verilator+seed+$seed >"$out/long-$init-$seed.log" 2>&1
 "$out/legacy-profile" "$out/m-tile-0.tsv" "$out/legacy-$init-$seed.jsonl" \
  +verilator+rand+reset+$init +verilator+seed+$seed >"$out/legacy-$init-$seed.log" 2>&1
 cmp "$baseline" "$out/legacy-$init-$seed.jsonl"
done
sha256sum "$out/"*.sv "$out/"*.cpp "$out/"*.tsv "$out/"*.log \
 "$out/"*.jsonl "$out/obj/longk-probe" "$out/legacy-profile" >"$out/output.sha256"
