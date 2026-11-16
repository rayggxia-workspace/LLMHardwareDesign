#!/bin/bash
#SBATCH --job-name=yzl-tile-window-rtl
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
archive=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/local-round6-tile-proof-20261109-v1/round6-tile-proof-source.tar.gz
echo "8cf33a18cfefab8314629ecefb35960906b4f84827d43aa6c7123910cd121886  $archive" | sha256sum -c -
sha256sum *.py *.sv *.cpp "$archive" > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
mkdir inputs
tar -xzf "$archive" -C inputs probes/column-v3-profile
cp -a inputs/probes/column-v3-profile proof
cp tb_column_tile_probe.sv column_tile_probe.py proof/
"$python" -B -c 'import hashlib,json,pathlib; p=pathlib.Path("proof/manifest.json"); m=json.loads(p.read_text()); m["parent_manifest_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest(); m["execution_order"]="packed-external-three-phase-v1"; m["sha256"].update({n:hashlib.sha256((p.parent/n).read_bytes()).hexdigest() for n in ("tb_column_tile_probe.sv","column_tile_probe.py")}); p.write_text(json.dumps(m,indent=2)+"\n")'
sim=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif)
"${sim[@]}" g++ -std=c++17 -O3 -Wall -Wextra -Werror native_tile_replay.cpp -o native-tile > build-native.log 2>&1
cat > native-tile-host <<'WRAPPER'
#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")" && pwd)
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif "$root/native-tile"
WRAPPER
chmod u+x native-tile-host
"$python" -u -B native_tile_probe.py ./native-tile-host native-probe --materialized > native-probe.log 2>&1
cd proof
iverilog="${2:?pass an installed qualified Icarus prefix}/bin/iverilog"
vvp="$2/bin/vvp"
"$iverilog" -g2012 -I. -Irtl/block_v2 -s tb_column_tile_probe -o sim -f compile.f > compile.log 2>&1
for init in 0 1 2; do
  "$vvp" sim +materialized +sinit="$init" > "simulate-$init.log" 2>&1
  "$python" -u -B ../column_tile_probe.py analyse . "simulate-$init.log" > "analyse-$init.log" 2>&1
  "$python" -B -c 'import json; m=json.load(open("summary.json")); assert m["materialized_order"]["cases"]==m["passed_cases"]'
  cp summary.json "summary-$init.json"
done
# Corrupt a saved golden output, never the RTL, and require a visible failure.
cp vectors.hex negative-vectors.original
"$python" -B -c 'import json,pathlib; m=json.load(open("manifest.json")); p=pathlib.Path("vectors.hex"); rows=p.read_text().splitlines(); i=m["cases"][0]["final"]; rows[i]=format(int(rows[i],16)^1,"016x"); p.write_text("\n".join(rows)+"\n")'
set +e
"$vvp" sim +materialized +sinit=2 > negative-simulate.log 2>&1
code=$?
set -e
cp negative-vectors.original vectors.hex
test "$code" -ne 0
grep -q 'FATAL' negative-simulate.log
cd ..
sha256sum proof/manifest.json proof/*log proof/summary*.json native-probe/report.json tests.log native-probe.log native-tile > output.sha256
