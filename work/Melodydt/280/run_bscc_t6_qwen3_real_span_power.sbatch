#!/usr/bin/env bash
#SBATCH --job-name=mdt-280realspan
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
        bash "$bundle/run_bscc_t6_qwen3_real_span_power.sbatch" inside \
        "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK" "$@"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/span-$3
replay=$root/real-activity/replay-${6:?payload replay job}
window=${7:?energy window}
stage=decode-live
if [[ $window == prefill ]]; then stage=prefill; fi
physical=$root/write-span/physical-38792114
netlist=$physical/flow/results/nangate45/s128_kv_store_scope/base
sources=$root/write-span-replay
(cd "$replay" && sha256sum --quiet -c results.sha256)
(cd "$physical" && sha256sum --quiet -c physical.sha256)
mkdir "$out"
python3 -B "$bundle/prepare_qwen3_real_span_cases.py" "$replay/$stage-w4-tile128-pr272-combined" "$window" "$out"
vlt=$4/verilator-5.042/bin/verilator
top=test_qwen3_write_span
"$vlt" --binary --timing --trace --trace-depth 2 --assert -j "$5" \
    --top-module "$top" --Mdir "$out/obj" -Wno-TIMESCALEMOD \
    "$bundle/$top.sv" "$sources/"{s128_kv_store_scope,s128_kv_row_transfer,s128_ddr64_store}.sv > "$out/build.log" 2>&1
export PYTHONPATH=$root/writer-power/frozen
for filename in "$out/"*.desc.hex; do
    label=$(basename "$filename" .desc.hex)
    for mode in 0 1; do
        for idle in 0 1; do
            case_dir=$out/$label-$mode-$idle
            mkdir "$case_dir"
            "$out/obj/V$top" "+DESC=$filename" "+PAYLOAD=$out/$label.data.hex" "+MODE=$mode" "+IDLE=$idle" \
                "+WAVE=$case_dir/raw.vcd" > "$case_dir/run.log"
            grep -Fq 'PASS span ' "$case_dir/run.log"
            python3 -B "$sources/measure_c639_writeback_window.py" "$netlist" "$case_dir" "$top/dut" 0 10450000 "$5"
        done
    done
done
python3 -B - "$out" <<'PY'
import json
from pathlib import Path
import sys
out=Path(sys.argv[1])
result=json.loads((out/"cases.json").read_bytes())
for name,row in result["cases"].items():
    row["incremental_pj_per_64b"]=[]
    for mode in (0,1):
        active=out/f"{name}-{mode}-0"
        idle=out/f"{name}-{mode}-1"
        for path,count in ((active,8),(idle,0)):
            activity=json.loads((path/"activity.json").read_bytes())
            if (activity["write_issued"],activity["write_retired"])!=(count,count):
                raise ValueError(f"unreconciled routed boundary: {path}")
        a=json.loads((active/"power/receipt.json").read_bytes())
        q=json.loads((idle/"power/receipt.json").read_bytes())
        row["incremental_pj_per_64b"].append((a["energy_nj"]-q["energy_nj"])*1000/8)
(out/"real-span-power.json").write_text(json.dumps(result,indent=2)+"\n")
PY
cd "$out"
sha256sum cases.json real-span-power.json *.hex */{activity.json,run.log} */power/receipt.json > results.sha256
sha256sum -c results.sha256
