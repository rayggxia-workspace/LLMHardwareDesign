#!/bin/bash
#SBATCH --job-name=yzl-command-controls
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
a=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
out="$1";hardware="$2"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/hardware:$PWD/compiler"
"$python" audits/command_pipeline_control_receipt.py "$out" "$hardware" --snapshot
mkdir -p "$out/tmp"
for family in p n e; do
 bash "$tool" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --xml-only --xml-output "$out/$family.xml" --timing -Wno-fatal --top-module "native_${family}_owner_control" -y rtl/projection -y rtl/control -y rtl/services -y rtl/resources -y rtl/p_services -y "$a/experiments/shared_x_control/rtl" -y "$a/rtl/block_local_native" -y "$a/rtl/w8a16_v1" -y "$a/rtl/s_sram" -y "$a/rtl/block_feed_v1" "rtl/control/native_${family}_owner_control.sv"
done

"$python" audits/command_pipeline_control_receipt.py "$out" "$hardware"
