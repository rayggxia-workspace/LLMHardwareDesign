#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
gds="$(realpath "${1:?}")"
proj="$(realpath ../..)"
run="$PWD/native-beol-${SLURM_JOB_ID:?}"
mkdir "$run"
cd "$run"
deck="$proj/issue-188-ucf16/accepted-ucf16-01/C16/FreePDK45.lydrc"
engine="$proj/issue-188-ucf16/well-engine-0309/release"
# The changed mask is metal3 only. Keep BEOL, off-grid and antenna
# expressions byte-identical, and retain the original gate definition.
python3 - "$deck" <<'PY'
from pathlib import Path
import sys
text=Path(sys.argv[1]).read_text()
flag="FEOL    = true"
gate="gate = poly &amp; active\n"
assert text.count(flag)==text.count(gate)==1
text=text.replace(flag,"FEOL    = false").replace(gate,"\n").replace("if ANTENNA\n","if ANTENNA\n"+gate)
Path("native-beol.lydrc").write_text(text)
PY
sha256sum "$deck" native-beol.lydrc "$gds" > input.sha256
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu
  --env "QT_QPA_PLATFORM=offscreen,LD_LIBRARY_PATH=$engine/usr/lib/klayout" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" "$engine/usr/bin/klayout" -v
"${runtime[@]}" "$engine/usr/bin/klayout" -b -r "$run/native-beol.lydrc" -rd "in_gds=$gds" -rd "report_file=$run/native.lyrdb" > native.log 2>&1
python3 - <<'PY'
import xml.etree.ElementTree as ET
n=len(ET.parse("native.lyrdb").findall(".//items/item"))
print("Native BEOL, off-grid and antenna markers:",n)
raise SystemExit(bool(n))
PY
