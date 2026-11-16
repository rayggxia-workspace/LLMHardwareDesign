#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mactivity
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
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_m_candidate_power.sbatch" inside \
        "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$@"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/m-$3
helper=$root/writer-power/frozen
product=$root/m-product/wide-38792112/replay-38792112
physical=$root/m-physical-exec/physical-38792357
mapped=$physical/flow/results/nangate45/m_exec_ready_300/base
mkdir "$out"
if [[ $5 == wave ]]; then
    (cd "$product" && sha256sum --quiet -c wide-results.sha256)
    awk '/^module m_native_leaf_s32\(/ {top=1}
         top && /^endmodule/ {exit}
         top && /^[[:space:]]+(input|output) / {print}' "$mapped/1_2_yosys.v" > "$out/m-ports.v"
    test -s "$out/m-ports.v"
    for mode in 0 1; do
        for stage in gate-up down writer-active; do
            sample=$product/DDR-$mode/ffn-$stage
            read -r label first last resolution < "$sample-signals.tsv"
            [[ $label == time && $resolution == -12 && $((last-first)) == 81920000 ]]
            mapfile -t scopes < <(awk -F '\t' '$1=="var" && $2 ~ /\/M$/ && $3=="a_ready" {print $2}' "$sample-signals.tsv")
            [[ ${#scopes[@]} == 3 ]]
            for site in "${!scopes[@]}"; do
                dest=$out/mode-$mode-$stage-p$site
                mkdir "$dest"
                "$helper/fst_scope_vcd" "$sample.fst" "$dest/raw.vcd" "${scopes[$site]}" > "$dest/extract.log"
                python3 -B "$helper/extract_c639_m_ports.py" "$out/m-ports.v" "$dest/raw.vcd" \
                    "$dest/ports.vcd" "${scopes[$site]}" "$first" "$last" 100
                rm -f -- "$dest/raw.vcd"
            done
        done
    done
    cd "$out"
    sha256sum "$mapped/1_2_yosys.v" "$product/wide-results.sha256" m-ports.v */ports.{vcd,json} > results.sha256
else
    [[ $5 == power ]]
    wave=$bundle/m-${6:?wave job ID}
    (cd "$wave" && sha256sum --quiet -c results.sha256)
    (cd "$physical" && sha256sum --quiet -c physical.sha256)
    export PYTHONPATH=$helper
    python3 -B - "$wave" "$out" "$mapped" "$4" <<'PY'
from pathlib import Path
import sys
from gate_power_300 import analyze
wave,out,netlist=map(Path,sys.argv[1:4])
for raw in sorted(wave.glob("*/ports.vcd")):
    analyze(raw,netlist,"dut",out/raw.parent.name,10000,0,81920000,int(sys.argv[4]))
PY
    cd "$out"
    sha256sum "$physical/physical.sha256" "$wave/results.sha256" */receipt.json > results.sha256
fi
sha256sum -c results.sha256
