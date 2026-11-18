#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmreal
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
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" "$opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_qwen3_pm_real.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$opt" "${1:?actual replay job}"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/pm-$3
vlt=$4/verilator-5.042/bin/verilator
project=$root/wide/wide-38772137/source/project
replay=$root/real-activity/replay-$5
bridge=$root/pm-bridge-power/pm-38793273
bank=$root/wide/sourcefs/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
(cd "$replay" && sha256sum --quiet -c results.sha256)
(cd "$bridge" && sha256sum --quiet -c results.sha256)
mkdir "$out"
python3 -B "$bundle/prepare_qwen3_pm_spans.py" "$replay" "$out"
compile() {
    local top=$1
    shift
    "$vlt" --binary --timing --trace --trace-depth 5 --assert -j 4 --timescale-override 1ns/1ps \
        --top-module "$top" --Mdir "$out/obj-$top" "$@" > "$out/build-$top.log" 2>&1
}
mother() {
    local top=test_qwen3_mother_pm
    compile "$top" "$bundle/test_qwen3_pm_arrays.sv" "$project/rtl/mother_control_v1/control_pm.sv" \
        "$project/rtl/s_sram/block_feed_s16k_sram.sv" "$bank"
    for size in 240 272 1616; do
        "$out/obj-$top/V$top" "+BYTES=$size" "+IMAGE=$out/mother-$size.128.hex" \
            "+WAVE=$out/mother-$size.vcd" > "$out/mother-$size.log"
        grep '^PASS mother PM ' "$out/mother-$size.log"
    done
}
sample_bridge() {
    local top=test_qwen3_pm_stream
    compile "$top" "$bundle/test_qwen3_pm_stream.sv" "$project/rtl/mother_control_native/native_pm_image_stream.sv"
    for file in "$out/"*.512.hex; do
        local label=$(basename "$file" .512.hex)
        local size=${label##*-}
        for mode in 0 1; do
            for idle in 0 1; do
                local case_dir=$out/$label-$mode-$idle
                mkdir "$case_dir"
                "$out/obj-$top/V$top" "+BYTES=$size" "+MODE=$mode" "+IDLE=$idle" +HOLD=1200 \
                    "+IMAGE=$file" "+WAVE=$case_dir/raw.vcd" > "$case_dir/run.log"
                grep -q '^PASS PM ' "$case_dir/run.log"
            done
        done
    done
}
mother & m=$!
sample_bridge & b=$!
status=0
wait "$m" || status=1
wait "$b" || status=1
((status==0))
export PYTHONPATH=$root/writer-power/frozen
python3 -B - "$out" "$bridge/flow/results/nangate45/native_pm_image_stream/base" <<'PY'
import json
from pathlib import Path
import sys
from extract_c639_m_ports import extract
from gate_power_300 import analyze

out,physical=map(Path,sys.argv[1:])
results={}
for wave in sorted(out.glob("*/raw.vcd")):
    normalized=wave.with_name("ports.vcd")
    extract(physical/"6_final.v",wave,normalized,"test_qwen3_pm_stream/dut",0,12050000,100,None)
    results[wave.parent.name]=analyze(normalized,physical,"dut",wave.parent/"power",10000,0,12050000,8)
receipt=json.loads((out/"pm-pages.json").read_bytes())
for label,row in receipt["samples"].items():
    row["bridge_incremental_nj"]=[results[f"{label}-{mode}-0"]["energy_nj"]-
                                  results[f"{label}-{mode}-1"]["energy_nj"] for mode in (0,1)]
(out/"pm-real-bridge-power.json").write_text(json.dumps(receipt,indent=2)+"\n")
PY
cd "$out"
sha256sum pm-pages.json pm-real-bridge-power.json *.hex mother-*.log mother-*.vcd \
    */{run.log,ports.json} */power/receipt.json > results.sha256
sha256sum -c results.sha256
