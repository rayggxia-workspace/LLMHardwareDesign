#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
cd "$root"
out="$root/evidence/architecture-revision-185/shared-read-plane-$SLURM_JOB_ID"
mkdir -p "$out/tmp"
export TMPDIR="$out/tmp"
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
serial=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/mother_control_native/native64_dma_serial_client.sv
"$v" -O0 --cc --exe --build -j 4 -Wno-fatal --top-module native_shared_read_plane  -GSERVICE_SERIAL_LIMIT=3 -GTRANSPORT_SERIAL_LIMIT=3  --Mdir "$out/obj" -CFLAGS '-std=c++17 -O1'  "$root/rtl/control/native_shared_read_plane.sv" "$root/rtl/control/native_shared_read_dma.sv" "$serial" "$root/tests/shared_read_plane.cpp" >"$out/build.log" 2>&1
for seed in 47 83 199; do
 "$out/obj/Vnative_shared_read_plane" "$seed" | tee "$out/result-$seed.txt"
done
