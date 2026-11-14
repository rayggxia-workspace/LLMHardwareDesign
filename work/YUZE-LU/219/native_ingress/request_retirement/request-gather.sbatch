#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
d=$3
rtl=$4
mother=$5
logits=$6
out="$PWD/request-gather-$SLURM_JOB_ID"
mkdir "$out"
archive="$d/mother-ingress-sNMsK9"
python3 -B stitch_request_index_gate.py "$archive/mother-run-110423/tb_u_gather_frame.sv" "$out/tb_u_gather_frame.sv"
python3 -B - "$archive/run-mother.sbatch" "$out/compile.sh" <<'PY'
import sys
from pathlib import Path
source, out = map(Path, sys.argv[1:])
runner = source.read_text()
start = runner.index('bash "$old/tool.sh" "$vlt"')
end = runner.index('bytes=$(wc -c',start)
head = runner[runner.index('root='):runner.index('out="$PWD/mother-run')]
compile = runner[start:end]
old = '"$out/tb_u_gather_frame.sv"'
assert compile.count(old) == 1
compile = compile.replace(old, old + ' "$cwd/native_request_index_gate.sv" '
    '"$rtl"/rtl/mother_control_native/native_{request_sequence,token_sequence,phase_page_sequence}.sv')
out.write_text(head+compile)
PY
cwd=$PWD
w="$g/ingress-route-iN0LbH"
source "$out/compile.sh"
for mode in normal stall; do
  bash "$old/tool.sh" "$out/obj/Vtb_u_gather_frame" "+image=$fixture/image.hex" "+row=$fixture/row.hex" \
    "+logits=$logits" "+bytes=$(wc -c < "$fixture/local.pm")" "+mode=$mode" "+mother=$mother" > "$out/$mode.log"
  grep '^PASS sequencer-to-Gather' "$out/$mode.log"
done
sha256sum "$out/"{tb_u_gather_frame.sv,normal.log,stall.log} "$mother" "$logits"
