#!/bin/bash
# Run on a compute node when using the project cluster.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd -P)
out=${1:?Pass a new output directory}
mkdir "$out"
out=$(cd "$out" && pwd -P)
v=${VERILATOR:-verilator}
jobs=${SLURM_CPUS_PER_TASK:-2}
"$v" --binary --timing --assert -Wno-fatal -j "$jobs" --Mdir "$out/obj-c" --top-module tb_c_native_remote \
 "$root/tb_c_native_remote.sv" "$root/release-support/native-rtl/C/ucf_s_compute_client.sv" \
 "$root/release-support/native-rtl/C/cfj_e32_port.sv" "$root/release-support/native-rtl/C/e_s32_ap64.sv" \
 "$root/release-support/native-rtl/C/e_s32_native.sv" > "$out/build-c.log" 2>&1
"$out/obj-c/Vtb_c_native_remote" | tee "$out/c-test.log"
"$v" --binary --timing --assert -Wno-fatal -j "$jobs" --Mdir "$out/obj-p" --top-module tb_p_native_windows \
 "$root/tb_p_native_windows.sv" "$root/release-support/native-rtl/P/private_a_tile_abort_frontend.sv" > "$out/build-p.log" 2>&1
"$out/obj-p/Vtb_p_native_windows" | tee "$out/p-test.log"
