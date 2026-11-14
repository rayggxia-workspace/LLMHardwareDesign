#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; overlay="$3"; pin_job="$4"
previous="$g/dma-m10-global-109793"
seal="$g/../joint-ddr-4C8sHe/dma-placed-odb.sha256"
sha256sum --check "$seal"
sha256sum --check "pin-audit-$pin_job.sha256"
db=$(cut -d ' ' -f 3- "$seal")
out="$PWD/stage-$SLURM_JOB_ID"
mkdir "$out"
python3 -B - "$g/plan_dma_m10.py" "$previous/landings.tsv" "$out/allocate.py" <<'PY'
from pathlib import Path
import sys
planner, reserved, dest = map(Path, sys.argv[1:])
source = planner.read_text()
anchor = 'with pins_path.open() as stream:'
assert source.count(anchor) == 1
source = source.replace(anchor, f'''
x_index = {{x: i for i, x in enumerate(xs)}}
y_index = {{y: j for j, y in enumerate(ys)}}
with Path({str(reserved)!r}).open() as previous:
    for row in previous:
        _, _, a, b, c, d = row.split()
        x, y = (int(a)+int(c))//2, (int(b)+int(d))//2
        blocked.add((x_index[x], y_index[y]))
''' + anchor)
dest.write_text(source)
PY
python3 -B "$out/allocate.py" "client3-$pin_job.tsv" "$previous/geometry.tsv" "$out/client3-landings.tsv"
cat "$previous/landings.tsv" "$out/client3-landings.tsv" > "$out/landings.tsv"
awk -F '\t' 'seen_p[$1]++ || seen_xy[$3 FS $4]++ {exit 1} END {if (NR!=5028) exit 1}' "$out/landings.tsv"
sed 's/\$ports != 4344/\$ports != 5028/' "$overlay/route-dma-port-gates.tcl" > "$out/route.tcl"
sha256sum "$out/client3-landings.tsv" "$out/landings.tsv" "$out/route.tcl" > "$out/landing-files.sha256"
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env NATIVE_DMA_ODB="$db" NATIVE_DMA_LANDINGS="$out/landings.tsv" \
  NATIVE_DMA_OUTPUT="$out" openroad -no_init -exit "$out/route.tcl"
sha256sum "$out/dma-grt.odb" "$out/route.guide" > "$out/global.sha256"
