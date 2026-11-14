#!/usr/bin/env bash
set -euo pipefail
cd "$1"
map="$2"; old_def="$3"
r=/public/home/yuzelu/project-circuit
frame="$r/issue250-u-native-frame-20261112-27"
tool="$r/issue250-u-n32-stored-link-20261112-01/tool.sh"
out="$PWD/frame-place-$SLURM_JOB_ID"
mkdir "$out"
python3 -B plan-frame-pins.py "$map/mapped.json" "$old_def" "$out"
bash "$tool" yosys -Q -p "read_json $out/with-output-ties.json; write_verilog -noattr $out/mapped.v" > "$out/netlist.log"
bash "$tool" env FRAME_SOURCE="$frame" GATHER_STAGE="$out" openroad -no_init -exit stage-frame.tcl
sha256sum "$out/"{mapped.v,pins.json,landings.tsv,staged-u.def,staged-u.odb} > "$out/artifacts.sha256"
