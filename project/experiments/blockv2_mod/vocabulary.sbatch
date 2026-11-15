#!/bin/bash
set -eu
a=$1
r=/public/home/yuzelu/project-circuit
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
mkdir -p tmp
"$r/issue250-u-n32-stored-link-20261112-01/tool.sh" "$v" --binary --timing --assert -Wno-fatal \
  --top-module test_s128_vocabulary_retire --Mdir "tmp/vocabulary-$SLURM_JOB_ID" \
  -y rtl -y "$a/rtl/s_sram" "$r/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v" rtl/test_s128_vocabulary_retire.sv
"$r/issue250-u-n32-stored-link-20261112-01/tool.sh" "$(pwd)/tmp/vocabulary-$SLURM_JOB_ID/Vtest_s128_vocabulary_retire"
