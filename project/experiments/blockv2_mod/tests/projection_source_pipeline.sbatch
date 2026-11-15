#!/bin/bash
#SBATCH --job-name=yzl-source-pipeline
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/source-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for mode in 0 1 2 3 4 5; do
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_projection_source_pipeline -GMODE=$mode --Mdir "$out/obj-$mode" tests/tb_projection_source_pipeline.sv rtl/services/projection_local_source.sv rtl/p_services/s128_ddr_range_load.sv rtl/projection/s32_a16_tile_quantizer.sv > "$out/build-$mode.log" 2>&1
bash "$tool" "$out/obj-$mode/Vtb_projection_source_pipeline" | tee "$out/run-$mode.log"
done

python3 tests/write_pipeline_receipt.py source "$SLURM_JOB_ID"
