#!/usr/bin/env bash
#SBATCH --job-name=mdt-280writepwr
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    wide_job=${1:-}
    (cd "$bundle" && sha256sum -c bundle.sha256)
    cd "$bundle/frozen"
    sha256sum -c source.sha256
    image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$image" \
        bash "$bundle/run_bscc_t6_c639_writeback_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$wide_job"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
out=$bundle/power-$3
cores=$4
wide_job=$5
frozen=$bundle/frozen
physical=$bundle/../writeback/physical-38769390
(cd "$physical" && sha256sum -c physical.sha256)
netlist=$physical/flow/results/nangate45/ffn_down_store_scope/base
scope=TOP/test_native_decode638_product_replay/feed_forward/down_output/writer
mkdir "$out"
measure() {
    local input=$1 mode=$2 phase=$3 first=$4 last=$5
    local sample=$out/mode-$mode-$phase
    mkdir "$sample"
    "$frozen/fst_scope_vcd" "$input" "$sample/raw.vcd" "$scope" > "$sample/extract.log"
    PYTHONPATH=$frozen python3 -B "$bundle/measure_c639_writeback_window.py" \
        "$netlist" "$sample" "$scope" "$first" "$last" "$cores"
    if [[ $phase == writer-active ]]; then
        python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["write_issued"] > 0' "$sample/activity.json"
    fi
}
if [[ -n $wide_job ]]; then
    run=$bundle/../wide/wide-$wide_job/replay-$wide_job
    (cd "$run" && sha256sum --quiet -c wide-results.sha256)
    for mode in 0 1; do
        read -r first last < <(awk '$1=="C639_ACTIVITY"&&$2=="writer-active" {print $3,$4}' "$run/replay-$mode.log")
        measure "$run/DDR-$mode/ffn-writer-active.fst" "$mode" writer-active "$first" "$last"
    done
else
    for mode in 0 1; do
        while read -r phase first last; do
            measure "$frozen/DDR-$mode/ffn-$phase.fst" "$mode" "$phase" "$first" "$last"
        done < "$frozen/activity-$mode.txt"
    done
fi
cd "$out"
sha256sum mode-*/{ports.json,activity.json,power/receipt.json,power/power.log} > results.sha256
sha256sum -c results.sha256
echo C639_FFN_WRITEBACK_WINDOWS_MEASURED
