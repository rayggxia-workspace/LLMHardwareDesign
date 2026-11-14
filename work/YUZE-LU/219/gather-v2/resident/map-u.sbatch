#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; w="$3"
root=/public/home/yuzelu/project-circuit
old="$root/issue250-u-n32-stored-link-20261112-01"
n="$root/issue252-native32-20261111-u-n32-physical03"
out="$PWD/map-$SLURM_JOB_ID"
mkdir "$out"
cat > "$out/map.ys" <<EOF
read_liberty -lib /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_slang --allow-use-before-declare --ignore-assertions --top u_n32_controlled_64 -G ENABLE_INDEXED_GATHER=1 -I$PWD -I$n/physical/lc $g/main-source/pu_native_lc.sv $w/source/u/ucf_native_service.sv $w/source/common/stored_link.sv $old/u_n32_s128_group.sv $old/pu_compact_e_service.sv $PWD/u_n32_controlled_64.sv $PWD/u_indexed_gather.sv $n/physical/leaves.sv
hierarchy -check -top u_n32_controlled_64
flatten -noscopeinfo
synth -top u_n32_controlled_64 -noabc
dfflibmap -liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
abc -exe $n/physical/abc_batch.py -liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib -D 3333
clean
check -assert
select -assert-count 1 t:n_s32_softmax_s128
select -assert-count 1 t:local_s_base
select -assert-count 1 t:block_v2_e_compact
stat -liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
write_verilog -noattr $out/mapped.v
EOF
bash "$old/tool.sh" env ISSUE250_ABC_TRANSPORT_DIR="$out" yosys -Q -s "$out/map.ys" > "$out/map.log" 2>&1
sha256sum "$out/"{map.ys,mapped.v,map.log}
