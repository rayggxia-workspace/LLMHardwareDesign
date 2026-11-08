#!/usr/bin/env bash
#SBATCH --job-name=yzl-native-sta
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%6
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
field_task=$3
kind=$(python3 -c 'import sys;print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env OMP_NUM_THREADS=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;root=$2;kind=$3;field_task=$4;r=project/experiments/upper_router
native=$root/attempt01/packages/$kind
if [[ $kind == P || $kind == U ]]; then views=$native/native/views; else views=$native/leaf-views; fi
python3 "$r/sta_config.py" "$native" "$root/attempt02/$kind-inventory.json" "$views" /OpenROAD-flow-scripts/flow/platforms/nangate45 "$task/$kind-config.json"
python3 "$r/native_sta.py" "$task/$kind-config.json" "$root/attempt05/$kind/backend/bindings.json" "$task/$kind"
out=$task/$kind
openroad -no_init -threads 10 -exit "$out/stitch.tcl" > "$out/stitch.log" 2>&1
field=$(cat "$field_task/$kind/selected-run.txt")
for projection in distributed driver farthest_sink; do
 for scale in 0 1 2; do
  name=$projection-coupling-$scale
  python3 "$r/stitch_rc.py" "$native/native/6_final.spef" "$root/attempt05/$kind/backend/bindings.json" "$root/attempt20/$kind/graph.json" "$root/attempt20/$kind/field/scene.json" "$field/rows.jsonl" "$out/$name.spef" --node-projection "$projection" --coupling-scale "$scale"
  export ROUTER_STITCHED_SPEF=$out/$name.spef ROUTER_STA_STEM=$out/$name
  openroad -no_init -threads 10 -exit "$out/sta.tcl" > "$out/$name.log" 2>&1
 done
done
python3 - "$out" <<"PY"
import json,re,sys
from pathlib import Path
out=Path(sys.argv[1]);rows=[]
for path in sorted(out.glob("*-counts.tsv")):
 counts={k:int(v) for k,v in (line.split() for line in path.read_text().splitlines())}
 stem=path.name[:-len("-counts.tsv")]
 summary=(out/(stem+"-summary.rpt")).read_text()
 slacks={k:float(v) for k,v in re.findall(r"worst slack (max|min) (-?[\d.]+)",summary)}
 rows.append({"variant":stem,"violations":counts,"slack_ns":slacks,
              "passed":set(slacks)=={"max","min"} and min(slacks.values())>=0 and not any(counts.values())})
result={"passed":len(rows)==9 and all(r["passed"] for r in rows),"variants":rows,
        "native_constraints_preserved":True,"original_liberty_limits":True,
        "scope":"actual native circuit plus fresh full-native-context upper RC; original TT300MHz constraints; node/Miller sensitivity"}
(out/"timing.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result));assert result["passed"]
PY
' bash "$task" "$root" "$kind" "$field_task"
