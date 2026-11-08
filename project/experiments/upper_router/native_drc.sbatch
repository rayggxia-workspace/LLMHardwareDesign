#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-drc
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
candidate=$2
kind=$(python3 -c 'import sys; print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
mkdir "$task/$kind"
test -f "$candidate/$kind/backend/physical-readback.json"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
run=$1; input=$2
deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc
printf "%s  %s\n" 4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147 "$deck" | sha256sum -c -
klayout -b -r "$deck" -rd "in_gds=$input/combined.gds" -rd "report_file=$run/native-full.lyrdb" > "$run/native-full.log" 2>&1
python3 - "$run" "$input" <<"PY"
import hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
run,source=map(Path,sys.argv[1:])
report=json.loads((source/"physical-readback.json").read_text())
assert report["geometry_passed"] and report["native_geometry_xor_zero"]
items=len(ET.parse(run/"native-full.lyrdb").findall(".//items/item"))
r={"full_original_native_deck_items":items,"native_drc_passed":items==0,
   "upper_research_geometry_passed":report["geometry_passed"],"source":str(source),
   "physical_qualified":False,"rc":"not_evaluated","timing":"not_evaluated",
   "scope":"complete original FreePDK45 deck on combined GDS, plus separate upper research rules; not calibrated 12-layer signoff"}
(run/"native-full.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r));assert items==0
PY
' bash "$task/$kind" "$candidate/$kind/backend"
