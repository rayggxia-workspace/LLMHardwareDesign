#!/usr/bin/env bash
#SBATCH --job-name=yzl-rc-annotation
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2;flat=$3
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;root=$2;flat=$3;r=project/experiments/upper_router
python3 "$r/assembly_sta.py" "$root/attempt17/base.json" "$root/attempt26/backend/bindings.json" "$flat/../configs.json" "$flat" "$task/sta"
python3 "$r/assemble_spef.py" "$root/attempt17/base.json" "$root/attempt17/library.json" "$root/attempt26/backend/bindings.json" "$task/native.spef"
export PYTHONPATH=$PWD/$r
python3 - "$task" "$root" <<"PY"
import json,sys
from pathlib import Path
from rc_graph import extract
from stitch_rc import stitch
task,root=map(Path,sys.argv[1:]);read=lambda p:json.loads(p.read_text())
graph=extract(read(root/"attempt26/spec.json"),read(root/"attempt26/routes.json"),dbu_per_micron=2000,sheet_resistance_ohm=.0102,via_resistance_ohm=.08)
binding=read(root/"attempt26/backend/bindings.json")
# Diagnostic only: native RC plus exact upper R, no upper C yet. No timing
# pass or electrical qualification is issued by this preflight.
spef=stitch((task/"native.spef").read_text(),binding,graph,{"ground":[],"coupling":[]})
(task/"annotation-only.spef").write_text(spef)
tcl=(task/"sta/sta.tcl").read_text().split("report_checks",1)[0]
(task/"annotation.tcl").write_text(tcl)
PY
export ROUTER_STITCHED_SPEF=$task/annotation-only.spef ROUTER_STA_STEM=$task/annotation
openroad -no_init -threads 10 -exit "$task/annotation.tcl" > "$task/annotation.log" 2>&1
python3 - "$task" <<"PY"
import json,re,sys
from pathlib import Path
out=Path(sys.argv[1]);log=(out/"annotation.log").read_text()
assert not re.search(r"\[ERROR |STA-0366|STA-0450|STA-0471|STA-0432",log)
drivers={f[2]+"/"+f[4] for line in (out/"sta/upper-owners.tsv").read_text().splitlines() if (f:=line.split("\t"))[1]=="OUTPUT"}
report=(out/"annotation-annotation.rpt").read_text()
missing={s.strip().replace("\\","") for s in report.splitlines() if re.match(r"^ \S",s)}
assert drivers and not drivers.intersection(missing),sorted(drivers.intersection(missing))
(out/"preflight.json").write_text(json.dumps({"passed":True,"upper_drivers_fully_annotated":len(drivers),"physical_qualified":False,"upper_C_extracted":False,"scope":"name and parasitic topology preflight only; final joint field C and STA still required"},indent=2)+"\n")
PY
' bash "$task" "$root" "$flat"
