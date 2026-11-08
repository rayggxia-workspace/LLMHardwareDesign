#!/usr/bin/env bash
#SBATCH --job-name=yzl-nine-drc
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
candidate=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;candidate=$2
test -f "$candidate/physical-readback.json"
deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc
printf "%s  %s\n" 4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147 "$deck" | sha256sum -c -
klayout -b -r "$deck" -rd "in_gds=$candidate/combined.gds" -rd "report_file=$task/native-full.lyrdb" > "$task/native-full.log" 2>&1
python3 - "$task" "$candidate" <<"PY"
import hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
out,candidate=map(Path,sys.argv[1:])
readback=json.loads((candidate/"physical-readback.json").read_text())
assert readback["geometry_passed"] and readback["native_geometry_xor_zero"]
count=len(ET.parse(out/"native-full.lyrdb").findall(".//items/item"))
result={"passed":count==0,"full_original_native_deck_items":count,
        "native_layer_xor_zero":True,"upper_research_geometry_passed":True,
        "combined_gds_sha256":readback["sha256"]["combined.gds"],
        "scope":"complete original FreePDK45 DRC plus research upper checks; not foundry calibrated 12-layer signoff"}
(out/"native-full.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result));assert count==0
PY
' bash "$task" "$candidate"
