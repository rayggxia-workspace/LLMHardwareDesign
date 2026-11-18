#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mholdidle
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c inputs.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" \
        "$opt/orfs-current-repacked.rootfs" bash "$bundle/run_bscc_t6_m_retained_idle.sbatch" \
        inside "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/hold-$3
source=$root/wide/wide-38772137/source/project/rtl/w8a16_v1
archive=$root/m-sta
wave=$root/m-baseline-power/m-38809661
empty=$root/m-baseline-power/idle-38809728
helper=$root/writer-power/frozen
(cd "$archive" && sha256sum --quiet -c inputs.sha256)
(cd "$wave" && sha256sum --quiet -c results.sha256)
(cd "$empty" && sha256sum --quiet -c results.sha256)
mkdir "$out" "$out/physical"
ln -s "$archive"/6_final.{odb,sdc,spef} "$wave/6_final.v" "$out/physical/"
python3 -B - "$empty/test_m_clocked_idle.sv" "$bundle/m_retained_idle_stimulus.sv" \
    "$out/test_m_retained_idle.sv" <<'PY'
from pathlib import Path
import sys

empty, stimulus, output = map(Path, sys.argv[1:])
interface, marker, _ = empty.read_text().partition("initial begin")
if not marker or interface.count("module test_m_clocked_idle;") != 1:
    raise ValueError("missing verified reset-empty fixture interface")
output.write_text(interface.replace("module test_m_clocked_idle;", "module test_m_retained_idle;")
                  + stimulus.read_text() + "\nendmodule\n")
PY

vlt=$4/verilator-5.042/bin/verilator
"$vlt" --version > "$out/verilator.txt"
"$vlt" --binary --timing --trace --trace-depth 2 --assert -j "$5" --timescale-override 1ns/1ps \
    --top-module test_m_retained_idle --Mdir "$out/obj" "$out/test_m_retained_idle.sv" \
    "$source/"{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32}.sv \
    > "$out/build.log" 2>&1
cd "$out"
./obj/Vtest_m_retained_idle > run.log
grep -q '^PASS old M retained scope' run.log
python3 -B "$helper/extract_c639_m_ports.py" "$wave/m-ports.v" idle.vcd ports.vcd test_m_retained_idle/dut 0 82920000 100
python3 -B "$helper/gate_power_300.py" ports.vcd physical dut power 10000 1000000 82920000 --cores "$5" --clip
python3 -B - "$empty/power/receipt.json" <<'PY'
import json
from pathlib import Path
import sys

held = json.loads(Path("power/receipt.json").read_bytes())
empty = json.loads(Path(sys.argv[1]).read_bytes())
for field in ("annotated", "timing"):
    if held[field] != empty[field]:
        raise ValueError(f"idle measurement differs in {field}")
if held["annotated"] != 1330:
    raise ValueError("incomplete routed M port annotation")
result = {
    "retained_scope_bias_idle_w": held["power_w"],
    "reset_empty_idle_w": empty["power_w"],
    "delta_total_w": held["power_w"]["total"] - empty["power_w"]["total"],
    "annotation": "The matched port waves drive routed activity propagation. Retained RTL state was checked by assertions.",
    "scope": "A valid BEGIN_SCOPE retains nonzero key, owner and bias. No weight record was fetched in this fixture.",
}
Path("comparison.json").write_text(json.dumps(result, indent=2) + "\n")
PY
sha256sum test_m_retained_idle.sv verilator.txt run.log ports.{vcd,json} power/receipt.json comparison.json > results.sha256
sha256sum -c results.sha256
