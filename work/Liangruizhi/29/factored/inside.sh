#!/bin/bash
set -euo pipefail
cd /work
export TMPDIR=/work/tmp
mkdir synth
yosys -V > synth/version.txt
sha256sum /usr/local/bin/yosys source/bank_port_fabric.sv > synth/input.sha256
(
  rc=0
  /usr/bin/time -v -o synth/frontend.time timeout 360 yosys -Q -T -l synth/frontend.log -p 'read_verilog -sv -defer -D SYNTHESIS source/bank_port_fabric.sv; hierarchy -check -top bank_port_fabric -chparam PORT_MODE 0 -chparam RESP_DEPTH 1; write_rtlil synth/elaborated.il' || rc=$?
  if [ "$rc" -eq 0 ]; then
    sha256sum synth/elaborated.il > synth/checkpoint.sha256
    /usr/bin/time -v -o synth/lowering.time timeout 720 yosys -Q -T -l synth/lowering.log -p 'read_rtlil synth/elaborated.il; proc; opt; memory_collect; check -assert; stat; write_json synth/generic.json' || rc=$?
  fi
  printf '%s\n' "$rc" > synth/exit.txt
) > synth/console.log 2>&1 &
syn=$!
sim_rc=0
python3 source/run_server.py --root /work --output /work/run-01 --jobs 3 --build-jobs 2 > simulation.log 2>&1 || sim_rc=$?
printf '%s\n' "$sim_rc" > simulation.exit
wait "$syn"
sha256sum synth/* simulation.log simulation.exit > finished.sha256
test "$sim_rc" -eq 0
test "$(cat synth/exit.txt)" -eq 0
