#!/usr/bin/env bash
set -euo pipefail
root=$1
cpus=${SLURM_CPUS_PER_TASK:?}
mkdir "$root/native-entry"
exec srun --exact -n1 -c "$cpus" --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root/source" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
root=$1; cpus=$2
out=$root/native-entry
python3 - "$out" <<"PY"
import sys
from pathlib import Path
sys.path.insert(0,"project/experiments/pu_leaf_base")
from controlled import stage, U_ENDPOINT, U_PORTS
out=Path(sys.argv[1]); stage(out,"U")
(out/"endpoint.sv").write_text("module pu_u_native_endpoint(input wire clk, reset, svc_valid, rsp_ready, input wire [1023:0] descriptor, output wire svc_ready, rsp_valid, output wire [15:0] status, output wire saturated, output wire [31:0] read_bytes, write_bytes,\n"+U_PORTS+");\n"+U_ENDPOINT+"endmodule\n")
PY
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator --binary --timing --assert -Wno-fatal --x-initial unique --x-assign unique -j "$cpus" --top-module tb_u_native_entry --Mdir "$out/obj" -Iproject/rtl/block_v2 \
 project/experiments/pu_leaf_base/tb_u_native_entry.sv "$out/endpoint.sv" "$out/lc/ucf_native_service.sv" "$out/lc/stored_link.sv" \
 project/rtl/block_v1/pu/{pu_u_group,pu_compact_e_service,pu_u_direct_pair}.sv project/rtl/block_v1/common/ucf_s_compute_client.sv \
 project/rtl/block_local_s/block_local_s_arbiter.sv project/rtl/s_sram/{local_s_base,block_feed_s16k_sram}.sv \
 project/rtl/block_v2/{block_v2_n,block_v2_n_group,block_v2_e_compact}.sv "$bank" > "$out/compile.log" 2>&1
for seed in 1:143 2:143 2:144; do
 "$out/obj/Vtb_u_native_entry" "+verilator+rand+reset+${seed%:*}" "+verilator+seed+${seed#*:}"
done
' bash "$root" "$cpus"
