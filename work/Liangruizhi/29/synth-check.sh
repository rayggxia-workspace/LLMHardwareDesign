#!/bin/bash
set -euo pipefail
export TMPDIR=/work/tmp
cd /work
yosys -V > synth-check/version.txt
sha256sum /usr/local/bin/yosys source/bank_port_fabric.sv > synth-check/input-sha256.txt
for mode in 0 1 2; do
 for depth in 1 2 4; do
  yosys -Q -T -l synth-check/m${mode}-d${depth}.log -p "read_verilog -sv -D SYNTHESIS source/bank_port_fabric.sv; hierarchy -check -top bank_port_fabric -chparam PORT_MODE $mode -chparam RESP_DEPTH $depth; proc; opt; memory_collect; check -assert; stat; write_json synth-check/m${mode}-d${depth}.json"
 done
done
