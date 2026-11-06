#!/usr/bin/env bash
set -euo pipefail
task=$1
shift
cpus=$SLURM_CPUS_PER_TASK
mkdir -p "$task/sim"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$task/source" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    out=$1/sim
    cpus=$2
    shift 2
    bankdir=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank
    bank=$bankdir/s_sram_256x128_freepdk45.v
    echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
    if (($# == 0)); then
      sources=(project/rtl/s_sram/{local_s_base,local_s_p,block_feed_s16k_sram}.sv
               project/rtl/block_feed_v1/block_feed_loader.sv)
    else
      test "$#" = 2
      std=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
      for odb in "$@"; do
        name=$(basename "$(dirname "$(dirname "$odb")")")
        test "$name" = local_s_base || test "$name" = local_s_p
        {
          printf "read_liberty {%s}\nread_liberty {%s}\nread_db {%s}\n" \
            "$std" "$bankdir/s_sram_256x128_freepdk45_TT_1p1V_25C.lib" "$odb"
          cat <<\TCL
set remove {}
foreach lib [[ord::get_db] getLibs] {
  foreach master [$lib getMasters] {
    set signal 0
    foreach term [$master getMTerms] {
      if {[$term getSigType] ni {POWER GROUND}} {set signal 1}
    }
    if {!$signal} {lappend remove [$master getName]}
  }
}
TCL
          printf "write_verilog -remove_cells \$remove {%s/%s.v}\n" "$out" "$name"
        } > "$out/$name.tcl"
        sha256sum "$odb"
        openroad -no_init -exit "$out/$name.tcl"
      done
      yosys -Q -p "read_liberty -ignore_miss_func -ignore_miss_dir $std; write_verilog -noattr $out/cells.v"
      sources=("$out"/{local_s_base,local_s_p,cells}.v)
    fi
    /public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator --binary --timing \
      -Wno-fatal --x-initial unique --x-assign unique --top-module test_compact_s -j "$cpus" --Mdir "$out" \
      project/experiments/compact_local_s/test_compact_s.sv "${sources[@]}" "$bank"
    for pair in 1:143 2:143 2:144; do
      echo "Run $pair"
      "$out/Vtest_compact_s" "+verilator+rand+reset+${pair%:*}" "+verilator+seed+${pair#*:}"
    done
  ' bash "$task" "$cpus" "$@"
