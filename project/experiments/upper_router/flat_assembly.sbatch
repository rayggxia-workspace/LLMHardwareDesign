#!/usr/bin/env bash
#SBATCH --job-name=yzl-flat-backend
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
config_dir=${3:-$root/attempt31}
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;root=$2;config_dir=$3;r=project/experiments/upper_router
python3 - "$task" "$root" "$config_dir" <<"PY"
import json,sys
from pathlib import Path
task,root=map(Path,sys.argv[1:3])
library=json.loads((root/"attempt17/library.json").read_text())
configs={name:json.loads((Path(sys.argv[3])/(name+"-config.json")).read_text()) for name in library["templates"]}
(task/"configs.json").write_text(json.dumps(configs,indent=2)+"\n")
PY
python3 "$r/flat_backend.py" "$root/attempt17/base.json" "$root/attempt17/library.json" "$root/attempt26/backend/bindings.json" "$root/attempt26/backend/upper.def" "$task/configs.json" "$root/attempt26/backend/technology/research12.tech.lef" "$root/attempt26/backend/upper-vias.lef" "$task/flat"
out=$task/flat
openroad -no_init -threads 10 -exit "$out/ingest.tcl" > "$out/ingest.log" 2>&1
export PYTHONPATH=$PWD/$r
python3 - "$root/attempt17/library.json" "$out" "$PWD/$r/snapshot.tcl" <<"PY"
from concurrent.futures import ThreadPoolExecutor
import json,os,subprocess,sys
from pathlib import Path
library=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);script=sys.argv[3]
def snapshot(item):
 name,meta=item;env=os.environ.copy();env.update(ROUTER_SNAPSHOT_ODB=meta["views"]["odb"]["path"],
  ROUTER_SNAPSHOT_INSTANCES=str(out/("source-"+name+"-instances.tsv")),
  ROUTER_SNAPSHOT_OWNERS=str(out/("source-"+name+"-owners.tsv")),
  ROUTER_SNAPSHOT_GEOMETRY=str(out/("source-"+name+"-geometry.tsv")))
 with (out/("source-"+name+"-snapshot.log")).open("xb") as log:
  subprocess.run(["openroad","-no_init","-threads","5","-exit",script],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(snapshot,sorted(library["templates"].items())))
PY
export ROUTER_SNAPSHOT_ODB=$out/assembled.odb ROUTER_SNAPSHOT_INSTANCES=$out/actual-instances.tsv ROUTER_SNAPSHOT_OWNERS=$out/actual-owners.tsv ROUTER_SNAPSHOT_GEOMETRY=$out/actual-geometry.tsv
openroad -no_init -threads 10 -exit "$r/snapshot.tcl" > "$out/actual-snapshot.log" 2>&1
export ROUTER_FLAT_OUT=$out ROUTER_FLAT_BINDING=$root/attempt26/backend/bindings.json
klayout -b -r "$r/physical_equivalence.py" > "$out/physical-equivalence.log" 2>&1
' bash "$task" "$root" "$config_dir"
