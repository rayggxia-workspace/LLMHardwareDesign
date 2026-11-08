#!/usr/bin/env bash
#SBATCH --job-name=yzl-resource-base
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
ir=$3
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
task=$1;root=$2;ir=$3
cd project/experiments/upper_router
python3 -B -m unittest test_router test_backend test_stage_package test_resource_base test_flow -v > "$task/tests.log" 2>&1
python3 resource_library.py "$task/source/work/YUZE-LU/230/inputs.json" "$root/attempt02" "$root/attempt01/packages" "$task/library.json"
python3 resource_base.py "$ir" "$task/library.json" "$task/base.json" --gap-dbu 160000 --alignment-dbu 16000
python3 - "$task" "$ir" <<"PY"
import json,sys
from pathlib import Path
from native_inventory import sha
from resource_base import read_base
task=Path(sys.argv[1]);base=read_base(task/"base.json")
summary={"source_ir_sha256":sha(sys.argv[2]),"base_sha256":sha(task/"base.json"),
 "group_instances":[a["id"] for a in base["assemblies"]],
 "independent_leaf_instances":len(base["leaf_instances"]),"actual_m10_endpoints":len(base["endpoints"]),
 "bounds_dbu":base["bounds_dbu"],"dbu_per_micron":base["dbu_per_micron"],
 "physical_qualified":False,"scope":"Actual resource-library placement assembled from #220 IR; not merged ODB or product signoff"}
(task/"resource-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary))
PY
' bash "$task" "$root" "$ir"
