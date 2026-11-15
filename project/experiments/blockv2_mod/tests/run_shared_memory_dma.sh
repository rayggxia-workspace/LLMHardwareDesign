#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
cd "$root"
out="$root/evidence/architecture-revision-185/shared-memory-dma-$SLURM_JOB_ID"
mkdir -p "$out/tmp"
export TMPDIR="$out/tmp"
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
"$v" -O0 --cc --exe --build -j 4 -Wno-fatal --top-module native_shared_memory_dma  --Mdir "$out/obj" -CFLAGS '-std=c++17 -O1'  "$root/rtl/control/native_shared_memory_dma.sv" "$root/tests/shared_memory_dma.cpp" >"$out/build.log" 2>&1
for config in "41 0" "79 2" "191 1"; do
 read -r seed initial <<< "$config"
 "$out/obj/Vnative_shared_memory_dma" "$seed" "$initial" "$out/trace-$seed.csv" | tee "$out/result-$seed.txt"
done

"$v" -O0 --cc --exe --build -j 4 -Wno-fatal --top-module native_shared_memory_dma -GSERIAL_LIMIT=3 --Mdir "$out/obj-small" -CFLAGS '-std=c++17 -O1' "$root/rtl/control/native_shared_memory_dma.sv" "$root/tests/shared_memory_dma.cpp" >"$out/build-small.log" 2>&1
"$out/obj-small/Vnative_shared_memory_dma" 269 2 "$out/trace-small.csv" | tee "$out/result-small.txt"
