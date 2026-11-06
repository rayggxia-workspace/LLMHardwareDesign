#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
gds="$(realpath "${1:?}")"
proj="$(realpath ../..)"
run="$PWD/native-complement-${SLURM_JOB_ID:?}"
mkdir "$run"
cd "$run"
deck="$proj/issue-188-ucf16/accepted-ucf16-01/C16/FreePDK45.lydrc"
engine="$proj/issue-188-ucf16/well-engine-0309/release"
# The unmodified deck evaluates IMPLANT.4 in a concurrently running job.
# Run the exact complement on the same canonical mask and engine.
python3 - "$deck" <<'PY'
from pathlib import Path
import sys
text=Path(sys.argv[1]).read_text()
match=[row for row in text.splitlines(keepends=True)
       if row.startswith("implant.space(45.nm, euclidian).output")]
assert len(match)==1
Path("drc-complement.lydrc").write_text(text.replace(match[0],"\n"))
PY
sha256sum "$deck" drc-complement.lydrc "$gds" > input.sha256
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu
  --env "QT_QPA_PLATFORM=offscreen,LD_LIBRARY_PATH=$engine/usr/lib/klayout" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" "$engine/usr/bin/klayout" -v
"${runtime[@]}" "$engine/usr/bin/klayout" -b -r "$run/drc-complement.lydrc" -rd "in_gds=$gds" -rd "report_file=$run/native.lyrdb" > native-complement.log 2>&1
python3 - <<'PY'
import xml.etree.ElementTree as ET
n=len(ET.parse("native.lyrdb").findall(".//items/item"))
print("Complement native markers:",n)
raise SystemExit(bool(n))
PY
