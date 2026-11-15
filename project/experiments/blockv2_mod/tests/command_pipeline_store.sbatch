#!/bin/bash
#SBATCH --job-name=yzl-store-pipeline
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/store-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for case in single multi read_error ack_error tag_error held_read held_write; do
args=()
case "$case" in single) args=(-GBURSTS=1);; read_error) args=(-GERROR=1);; ack_error) args=(-GERROR=2);; tag_error) args=(-GERROR=3);; held_read) args=(-GERROR=1 -GHELD=1);; held_write) args=(-GERROR=1 -GHELD=2);; esac
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_store_pipeline "${args[@]}" --Mdir "$out/obj-$case" tests/tb_store_pipeline.sv rtl/p_services/s128_store_pipeline.sv > "$out/build-$case.log" 2>&1
bash "$tool" "$out/obj-$case/Vtb_store_pipeline" | tee "$out/run-$case.log"
done

for error in 0 1 2 3 4; do
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_store_scope -GERROR=$error --Mdir "$out/scope-$error" tests/tb_store_scope.sv rtl/p_services/s128_store_pipeline.sv rtl/p_services/s128_kv_store_scope.sv > "$out/build-scope-$error.log" 2>&1
bash "$tool" "$out/scope-$error/Vtb_store_scope" | tee "$out/run-scope-$error.log"
done
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python audits/command_pipeline_store_receipt.py "$SLURM_JOB_ID"
