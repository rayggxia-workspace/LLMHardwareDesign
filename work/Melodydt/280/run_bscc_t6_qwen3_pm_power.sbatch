#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmbridge
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
        bash "$bundle/run_bscc_t6_qwen3_pm_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK" "${1:?component check job ID}"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/pm-$3
check=$6
reference=$root/component-checks/check-$check
source_file=$root/wide/wide-38772137/source/project/rtl/mother_control_native/native_pm_image_stream.sv
cpus=$5
mkdir "$out"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = native_pm_image_stream
export SYNTH_HDL_FRONTEND = slang
export VERILOG_FILES = $source_file
export SDC_FILE = $root/write-span/target.sdc
export DIE_AREA = 0 0 160 160
export CORE_AREA = 10 10 150 150
export PLACE_DENSITY = 0.55
EOF
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$((cpus-2))" finish > "$out/flow.log" 2>&1 &
flow=$!
trap 'wait "$flow" || true' EXIT
vlt=$4/verilator-5.042/bin/verilator
top=test_qwen3_pm_stream
"$vlt" --binary --timing --trace --trace-depth 2 --assert -j 2 --top-module "$top" \
    --Mdir "$out/obj" "$bundle/$top.sv" "$source_file" > "$out/build.log" 2>&1
for size in 352 1664; do
    for mode in 0 1; do
        for idle in 0 1; do
            case_dir=$out/$size-$mode-$idle
            mkdir "$case_dir"
            "$out/obj/V$top" "+BYTES=$size" "+IMAGE=$reference/pm-$size.hex" \
                "+MODE=$mode" "+IDLE=$idle" +HOLD=1200 "+WAVE=$case_dir/raw.vcd" > "$case_dir/run.log"
        done
    done
done
wait "$flow"
trap - EXIT
export PYTHONPATH=$root/writer-power/frozen
key=nangate45/native_pm_image_stream/base
python3 -B - "$out" "$key" "$top" "$cpus" <<'PY'
from pathlib import Path
import sys
from extract_c639_m_ports import extract
from gate_power_300 import analyze

out,key,top,cpus=sys.argv[1:]
out=Path(out)
physical=out/"flow/results"/key
for raw in sorted(out.glob("*/raw.vcd")):
    times=[int(line[1:]) for line in raw.open() if line.startswith("#")]
    if times[0]!=0 or times[-1]!=12050000:
        raise ValueError(f"unexpected fixed sample extent: {raw}")
    wave=raw.with_name("ports.vcd")
    extract(physical/"6_final.v",raw,wave,top+"/dut",0,12050000,100,None)
    analyze(wave,physical,"dut",raw.parent/"power",10000,0,12050000,int(cpus))
PY
cd "$out"
sha256sum config.mk */{run.log,ports.json} */power/receipt.json \
    "flow/results/$key/"6_final.{v,odb,sdc,spef} "flow/logs/$key/6_report.json" > results.sha256
sha256sum -c results.sha256
