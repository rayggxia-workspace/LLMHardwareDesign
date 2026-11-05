#!/usr/bin/env bash
# Run from a checkout with Verilator 5 and a C++ compiler supporting timing.
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: bash $0 <OpenRAM bank .v> <new output directory>" >&2
    exit 2
fi
bank=$(realpath -e -- "$1")
out=$(realpath -m -- "$2")
mkdir -- "$out"
cd "$(dirname "$0")/../../.."
experiment=$PWD/project/experiments/block_local_s
rtl=$PWD/project/rtl
common=(
    --cc --exe --build -j "${BUILD_JOBS:-4}" --assert
    --x-initial unique --x-assign unique --top-module local_s_pool
    "$rtl/block_feed_v1/block_feed_s16k.sv"
    "$rtl/block_feed_v1/block_feed_loader.sv"
    "$rtl/block_local_s/block_local_s_arbiter.sv"
    "$rtl/block_local_s/block_local_s_macro.sv"
    "$experiment/local_s_pool.sv" "$experiment/test_local_s.cpp"
)
verilator=${VERILATOR:-verilator}
"$verilator" --version >"$out/tool.txt"
sha256sum "$bank" >"$out/bank.sha256"

"$verilator" "${common[@]}" --Mdir "$out/cells" >"$out/build-cells.log" 2>&1
"$verilator" "${common[@]}" --Mdir "$out/sram" "-GUSE_SRAM=1'b1" \
    --timing --timescale-override 1ns/1ns -CFLAGS -DLOCAL_S_TIMED_BANK \
    "$rtl/s_sram/block_feed_s16k_sram.sv" "$bank" >"$out/build-sram.log" 2>&1

for backend in cells sram; do
    for init in 0 1 2; do
        for seed in 177 1001 9001; do
            log="$out/$backend-init$init-seed$seed.log"
            "$out/$backend/Vlocal_s_pool" "+verilator+rand+reset+$init" \
                "+verilator+seed+$seed" "--seed=$seed" 2>&1 | \
                awk '/^CASE_PASS|^FAIL|^\{|^%Error|^Aborting/ || !/^[[:space:]]*[0-9]+ (Reading|Writing) /' >"$log"
            test "$(grep -c '^CASE_PASS' "$log")" -eq 7
            grep -F '{"pass":true' "$log"
        done
    done
done
