#!/usr/bin/env bash
set -euo pipefail
src=${1:?pinned PR214 source directory}
out=${2:?output directory}
slot=${3:?native bench number}
bank=${SRAM_BANK:?qualified SRAM model}
verilator=${VERILATOR:-verilator}
mkdir -p "$out"
out=$(cd "$out" && pwd)
cd "$src"
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
common=(project/rtl/s_sram/{local_s_base,local_s_p,block_feed_s16k_sram}.sv
        project/rtl/block_feed_v1/block_feed_loader.sv)
case "$slot" in
  0) top=tb_pu_p_store
     sources=(project/rtl/block_local_s/block_local_s_arbiter.sv project/rtl/pu_leaf_base/pu_p_store_control.sv) ;;
  1) top=tb_pu_compact_e
     sources=(project/rtl/block_v2/{block_v2_e,block_v2_e_compact}.sv project/rtl/pu_leaf_base/pu_compact_e_service.sv) ;;
  2) top=tb_pu_p_group
     sources=(project/rtl/block_local_s/block_local_s_arbiter.sv
       project/rtl/block_v2/{block_v2_m,block_v2_g}.sv
       project/rtl/pu_leaf_base/{pu_p_group,pu_p_store_control,pj_feed_hold,pj_mem_port,pj_sram_client}.sv) ;;
  3) top=tb_pu_u_group
     sources=(project/rtl/block_local_s/block_local_s_arbiter.sv
       project/rtl/block_v2/{block_v2_n,block_v2_n_group,block_v2_e,block_v2_e_compact}.sv
       project/rtl/pu_leaf_base/{pu_u_group,pu_compact_e_service,pu_u_direct_pair,ucf_s_compute_client}.sv) ;;
  *) exit 2 ;;
esac
"$verilator" --binary --timing --assert -Wno-fatal --x-initial unique --x-assign unique \
  -Iproject/rtl/block_v2 -j "${BUILD_JOBS:-4}" --top-module "$top" --Mdir "$out/obj" \
  "project/experiments/pu_leaf_base/$top.sv" "${common[@]}" "${sources[@]}" "$bank" > "$out/compile.log" 2>&1
for init in 1:143 2:143 2:144; do
  "$out/obj/V$top" "+verilator+rand+reset+${init%:*}" "+verilator+seed+${init#*:}" > "$out/run-${init/:/-}.log" 2>&1
  grep -E '^PASS' "$out/run-${init/:/-}.log"
done
(cd "$out" && sha256sum compile.log run-*.log > result.sha256)
