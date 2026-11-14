#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
d=$3
link="$d/mother-ingress-sNMsK9/link-110415"
out="$PWD/gather-topology-$SLURM_JOB_ID"
mkdir "$out"
python3 -B bind_gather_mother_topology.py "$link/mother.pm" "$link/request-link.json" \
  "$d/geometry-110384/base.json" "$d/decode-program-110370/local.pm" "$out/native"
python3 -B - "$d" "$out" <<'PY'
import sys
from pathlib import Path
d,out=map(Path,sys.argv[1:])
fixture=(d/'mother-ingress-sNMsK9/mother-run-110423/tb_u_gather_frame.sv').read_text()
old='assert(mother_image[4][0+:32]==TOPOLOGY);'
assert fixture.count(old)==1
(out/'tb_u_gather_frame.sv').write_text(fixture.replace(old,
  'assert(mother_image[4][0+:32]==32\'d25001 && image[4][0+:32]==TOPOLOGY);')
  .replace('$readmemh(mother_path,mother_image);', '$readmemh(mother_path,mother_image);\n    $readmemh(image_path,image);'))
runner=(d/'mother-ingress-sNMsK9/run-mother.sbatch').read_text()
start=runner.index('bash "$old/tool.sh" "$vlt"')
end=runner.index('bytes=$(wc -c',start)
head=runner[runner.index('root='):runner.index('out="$PWD/mother-run')]
(out/'compile.sh').write_text(head+runner[start:end])
PY
export g d out
w="$g/ingress-route-iN0LbH"
source "$out/compile.sh"
for mode in normal stall; do
  bash "$old/tool.sh" "$out/obj/Vtb_u_gather_frame" "+image=$fixture/image.hex" "+row=$fixture/row.hex" \
    "+logits=$fixture/logits.hex" "+bytes=$(wc -c < "$fixture/local.pm")" "+mode=$mode" "+mother=$out/native/mother.hex" > "$out/$mode.log"
  grep '^PASS mother-to-U0 Gather' "$out/$mode.log"
done
sha256sum "$out/native/"{mother.pm,mother.hex} "$out/"{tb_u_gather_frame.sv,normal.log,stall.log}
