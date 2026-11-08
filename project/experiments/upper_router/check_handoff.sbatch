#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-check
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
candidate=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env "OMP_NUM_THREADS=10,QT_QPA_PLATFORM=offscreen" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;candidate=$2
for script in project/experiments/upper_router/*.sbatch; do bash -n "$script"; done
openroad -version > "$task/openroad-version.txt" 2>&1
klayout -v > "$task/klayout-version.txt" 2>&1
sha256sum "$(command -v openroad)" "$(command -v klayout)" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif > "$task/tools.sha256"
cd project/experiments/upper_router
python3 -B -m unittest test_router test_backend test_stage_package -v > "$task/tests.log" 2>&1
python3 - "$task" "$candidate" <<"PY"
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,os
from backend import emit
task,source=map(Path,sys.argv[1:]);passed=[]
for kind in ("P","U","C","F","J"):
 base=source/kind
 spec=json.loads((base/"spec.json").read_text());routes=json.loads((base/"routes.json").read_text())
 out=task/(kind+"-final-emitter")
 emit(spec,routes,out,2000,via_resistance_ohm=0.08)
 for name in ("upper.def","upper-vias.lef"):
  assert (out/name).read_bytes()==(base/"backend"/name).read_bytes(),(kind,name)
 passed.append(kind)
negative=[]
for name in ("missing-via","wrong-native-hash"):
 out=task/name;out.mkdir()
 for filename in ("bindings.json","odb-geometry.tsv"):
  shutil.copyfile(source/"P/backend"/filename,out/filename)
 if name=="missing-via":
  p=out/"odb-geometry.tsv";lines=p.read_text().splitlines()
  i=next(i for i,l in enumerate(lines) if "\tvia11\t" in l)
  del lines[i];p.write_text("\n".join(lines)+"\n")
 else:
  p=out/"bindings.json";m=json.loads(p.read_text());m["context"]["native_gds_sha256"]="0"*64
  p.write_text(json.dumps(m))
 env=dict(os.environ,ROUTER_HANDOFF=str(out),ROUTER_NATIVE_GDS=str(source.parent/"attempt01/packages/P/native/6_final.gds"))
 result=subprocess.run(["klayout","-b","-r","physical_readback.py"],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/"rejection.log").write_text(result.stdout)
 reason="DEF/OpenDB geometry differs" if name=="missing-via" else "native GDS fingerprint mismatch"
 assert result.returncode!=0 and reason in result.stdout,(name,result.stdout)
 negative.append({"case":name,"rejected":True,"reason":reason})
(task/"handoff-check.json").write_text(json.dumps({"final_emitter_matches_executed_geometry":passed,"negative_controls":negative},indent=2)+"\n")
print(json.dumps(negative))
PY
' bash "$task" "$candidate"
