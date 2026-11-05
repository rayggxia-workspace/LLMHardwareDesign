#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-gate
#SBATCH --partition=c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=36
#SBATCH --time=UNLIMITED
#SBATCH --output=gate-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
[[ $# -eq 3 ]]
for dir in "$@"; do test -s "$dir/physical-functional.v"; done
work="$PWD/gate-$SLURM_JOB_ID"
mkdir "$work"
testbench="$PWD/tb_block_ucf16.sv"
cd "$work"
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
printf 'read_liberty -ignore_miss_func -ignore_miss_dir /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib\nwrite_verilog -noattr cells.v\n' > cells.ys
runtime=("$pinned" exec --cleanenv --bind /public/home/yuzelu --pwd "$work" "$image")
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec yosys -s cells.ys' > cells.log 2>&1
export LC_ALL=C
sha256sum "$1/physical-functional.v" "$2/physical-functional.v" "$3/physical-functional.v" "$testbench" cells.v > inputs.sha256
"${runtime[@]}" "$verilator" --binary --timing --assert --timescale-override 1ns/1ns \
    --x-initial unique --x-assign unique -DUCF_FINAL_NETLIST --top-module tb_block_ucf16 \
    -MAKEFLAGS OPT_FAST=-O0 -MAKEFLAGS OPT_SLOW=-O0 \
    -j "${SLURM_CPUS_PER_TASK}" -Wno-PINMISSING -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND \
    "$testbench" "$1/physical-functional.v" "$2/physical-functional.v" "$3/physical-functional.v" cells.v "$bank" \
    > compile.log 2>&1
for spec in 1:121 2:121 2:122; do
    IFS=: read -r mode seed <<< "$spec"
    logfile="mode-$mode-seed-$seed.log"
    "${runtime[@]}" ./obj_dir/Vtb_block_ucf16 "+verilator+rand+reset+$mode" "+verilator+seed+$seed" > "$logfile" 2>&1
    test "$(grep -c 'real-SRAM compute and writeback' "$logfile")" -eq 3
    grep -qx 'PASS C-U-C held-source SRAM handoff' "$logfile"
    grep -qx 'PASS C interrupt and restart' "$logfile"
done
sha256sum compile.log mode-*.log > results.sha256
printf '%s\n' 'PASS final ODB netlist, three initial conditions'
