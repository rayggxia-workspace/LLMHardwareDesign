#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
kind="${1:?}"; candidate="${2:-}"; if [[ -n "$candidate" ]]; then candidate="$(realpath "$candidate")"; fi
work="$base/function-$SLURM_JOB_ID"
mkdir "$work"
cd "$work"
repo="$(realpath ../../..)"
platform=/OpenROAD-flow-scripts/flow/platforms/nangate45
printf 'read_liberty -ignore_miss_func -ignore_miss_dir %s/lib/NangateOpenCellLibrary_typical.lib\nwrite_verilog -noattr cells.v\n' "$platform" > cells.ys
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec yosys -s cells.ys' > cells.log 2>&1
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
args=(--binary --timing --assert --timescale-override 1ns/1ns --x-initial unique --x-assign unique -j "$SLURM_CPUS_PER_TASK" -Wno-fatal)
if [[ $kind == P ]]; then
    top=tb_pj
    pj="$repo/issue-187-p16-j16/139-p-final-gates/gates/P-electrical"
    candidate="${candidate:-$base/eco-98042-0}"
    testbench="$base/tb_pj.sv"
    if [[ $# -ge 2 ]]; then
        python3 - "$testbench" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
source=source.replace("wire route_valid,route_take;", "wire route_valid,route_take,relayed_valid;")
source=source.replace(".g_from_m_valid(bridge && route_valid)",
    ".upper_valid_in(route_valid),.upper_valid_out(relayed_valid),.g_from_m_valid(bridge && relayed_valid)")
assert ".upper_valid_out(relayed_valid)" in source
Path("tb_pj_relay.sv").write_text(source)
PY
        testbench="$work/tb_pj_relay.sv"
    fi
    sources=("$testbench" "$base/sram_model.sv" "$candidate/eco-routed.v" "$pj"/{p4,M,G}-odb.v)
    args+=(-DTEST_P --output-split 12000 --output-split-cfuncs 150 --output-groups 0 -CFLAGS -O1)
    trials=(0:187 1:188 2:189)
else
    top=tb_block_ucf16
    sources=("$base/tb_block_ucf16.sv" "$base/eco-98057-2/eco-routed.v" "$base/eco-98057-1/eco-routed.v"
      "$repo/issue-188-ucf16/accepted-ucf16-01/F16/physical-functional.v"
      "$repo/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v")
    args+=(-DUCF_FINAL_NETLIST -MAKEFLAGS OPT_FAST=-O0 -MAKEFLAGS OPT_SLOW=-O0 -Wno-PINMISSING -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND)
    trials=(1:121 2:121 2:122)
fi
sha256sum cells.v "${sources[@]}" > input.sha256
"${runtime[@]}" "$verilator" "${args[@]}" --top-module "$top" cells.v "${sources[@]}" > compile.log 2>&1
for trial in "${trials[@]}"; do
    mode=${trial%:*}
    seed=${trial#*:}
    log="run-$mode-$seed.log"
    "${runtime[@]}" "./obj_dir/V$top" "+verilator+rand+reset+$mode" "+verilator+seed+$seed" > "$log" 2>&1
    if [[ $kind == P ]]; then
        grep -q 'PASS P16 ' "$log"
    else
        [[ $(grep -c 'real-SRAM compute and writeback' "$log") == 3 ]]
        grep -qx 'PASS C-U-C held-source SRAM handoff' "$log"
        grep -qx 'PASS C interrupt and restart' "$log"
    fi
done
sha256sum run-*.log > results.sha256
echo 'PASS final ECO netlist, three initial conditions'
