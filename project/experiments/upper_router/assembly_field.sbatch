#!/usr/bin/env bash
#SBATCH --job-name=yzl-nine-field
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%5
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
topology=$3
index=$SLURM_ARRAY_TASK_ID
mkdir "$task/shard-$index"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
task=$1;root=$2;index=$3;topology=$4;r=project/experiments/upper_router;out=$task/shard-$index
python3 "$r/rc_graph.py" "$root/attempt26/spec.json" "$root/attempt26/routes.json" "$out/graph.json" --dbu-per-micron 2000 --sheet-resistance-ohm .0102 --via-resistance-ohm .08
python3 - "$topology/topology.json" "$index" "$out/layers.txt" <<"PY"
import json,sys
from pathlib import Path
counts=json.loads(Path(sys.argv[1]).read_text())["shape_counts"]
groups=[[] for _ in range(5)];loads=[0]*5
for name in sorted(counts,key=lambda n:(-counts[n],n)):
 i=min(range(5),key=lambda i:(loads[i],i));groups[i].append(name);loads[i]+=max(1,counts[name])
Path(sys.argv[3]).write_text(",".join(groups[int(sys.argv[2])]))
PY
export ROUTER_FIELD_OUT=$out/field ROUTER_HANDOFF=$root/attempt26/backend ROUTER_TOPOLOGY=$topology ROUTER_RC_GRAPH=$out/graph.json ROUTER_TECH_LEF=$root/attempt26/backend/technology/research12.tech.lef
export ROUTER_NATIVE_LAYERS=$(cat "$out/layers.txt") ROUTER_INCLUDE_UPPER=0
if [[ $index == 0 ]]; then export ROUTER_INCLUDE_UPPER=1; fi
klayout -b -r "$r/field_context.py"
' bash "$task" "$root" "$index" "$topology"
