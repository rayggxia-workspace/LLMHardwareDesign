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
action=$5
if [[ $action == baseline-* ]]; then
    product=$root/wide/wide-38772137/replay-38772137
    physical=$root/m-sta
    action=${action#baseline-}
fi
mkdir "$out"
if [[ $action == wave ]]; then
    (cd "$product" && sha256sum --quiet -c wide-results.sha256)
    reference=$mapped/1_2_yosys.v
    if [[ $5 == baseline-wave ]]; then
        (cd "$physical" && sha256sum --quiet -c inputs.sha256)
        export M_ARCHIVE_DB=$physical/6_final.odb M_ARCHIVE_NETLIST=$out/6_final.v
        cat > "$out/export.tcl" <<'TCL'
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(M_ARCHIVE_DB)
write_verilog $::env(M_ARCHIVE_NETLIST)
TCL
        openroad -no_init -threads "$4" -exit "$out/export.tcl" > "$out/export.log" 2>&1
        reference=$M_ARCHIVE_NETLIST
    fi
    awk '/^module[[:space:]]+m_native_leaf_s32[[:space:]]*\(/ {top=1}
         top && /^endmodule/ {exit}
         top && /^[[:space:]]+(input|output) / {print}' "$reference" > "$out/m-ports.v"
    test -s "$out/m-ports.v"
    for mode in 0 1; do
        for stage in gate-up down writer-active; do
            sample=$product/DDR-$mode/ffn-$stage
            signals=$sample-signals.tsv
            if [[ $5 == baseline-wave ]]; then
                signals=$root/wave-audit/audit-38782228/mode-$mode-$stage/signal-table.tsv
            fi
            read -r label first last resolution < "$signals"
            [[ $label == time && $resolution == -12 && $((last-first)) == 81920000 ]]
            mapfile -t scopes < <(awk -F '\t' '$1=="var" && $2 ~ /\/M$/ && $3=="a_ready" {print $2}' "$signals")
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
    sha256sum "$reference" "$product/wide-results.sha256" m-ports.v */ports.{vcd,json} > results.sha256
else
    [[ $action == power ]]
    wave=$bundle/m-${6:?wave job ID}
    (cd "$wave" && sha256sum --quiet -c results.sha256)
    export PYTHONPATH=$helper
    netlist=$mapped
    manifest=$physical/physical.sha256
    workers=1
    if [[ $5 == baseline-power ]]; then
        (cd "$physical" && sha256sum --quiet -c inputs.sha256)
        manifest=$physical/inputs.sha256
        netlist=$out/physical
        mkdir "$netlist"
        ln -s "$physical"/6_final.{odb,sdc,spef} "$wave/6_final.v" "$netlist/"
        workers=3
    else
        (cd "$physical" && sha256sum --quiet -c physical.sha256)
    fi
    python3 -B - "$wave" "$out" "$netlist" "$4" "$workers" <<'PY'
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import sys
import gate_power_300 as gate

wave,out,netlist=map(Path,sys.argv[1:4])
workers=int(sys.argv[5])
threads=int(sys.argv[4])//workers
gate.sha=lru_cache(maxsize=None)(gate.sha)

def measure(raw):
    gate.analyze(raw,netlist,"dut",out/raw.parent.name,10000,0,81920000,threads)

with ThreadPoolExecutor(max_workers=workers) as pool:
    list(pool.map(measure,sorted(wave.glob("*/ports.vcd"))))
PY
    if [[ $5 == baseline-power ]]; then
        python3 -B "$bundle/summarize_m_baseline_power.py" "$wave" "$out" "$physical/sta-38771837/sta.log"
    fi
    cd "$out"
    sha256sum "$manifest" "$wave/results.sha256" */receipt.json > results.sha256
    if [[ $5 == baseline-power ]]; then
        sha256sum baseline-power.json >> results.sha256
    fi
fi
sha256sum -c results.sha256
