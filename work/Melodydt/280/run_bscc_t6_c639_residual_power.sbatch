#!/usr/bin/env bash
#SBATCH --job-name=mdt-280respower
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
    sha256sum -c bundle.sha256
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_c639_residual_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/power-$3
run=$root/wide/wide-38772137/replay-38772137
helper=$root/writer-power/frozen
physical=$root/residual/physical-38771074
(cd "$physical" && sha256sum -c physical.sha256)
netlist=$physical/flow/results/nangate45/s128_kv_store_scope/base
mkdir "$out"
for mode in 0 1; do
    for stage in gate-up down writer-active; do
        fst=$run/DDR-$mode/ffn-$stage.fst
        sample=$out/mode-$mode-$stage
        mkdir "$sample"
        "$helper/fst_scope_table" "$fst" > "$sample/signal-table.tsv"
        scope=$(awk -F '\t' '$1=="var" && $2 ~ /feed_forward\/next_layer\/store$/ && $3 ~ /^wr_data/ && $4==512 {print $2; exit}' "$sample/signal-table.tsv")
        if [[ -z $scope ]]; then
            printf '%s\t%s\t%s\n' "$mode" "$stage" absent >> "$out/coverage.tsv"
            continue
        fi
        read -r first last < <(awk -v s="$stage" '$1=="C639_ACTIVITY" && $2==s {print $3,$4}' "$run/replay-$mode.log")
        "$helper/fst_scope_vcd" "$fst" "$sample/raw.vcd" "$scope" > "$sample/extract.log"
        PYTHONPATH=$helper python3 -B "$bundle/measure_c639_writeback_window.py" \
            "$netlist" "$sample" "$scope" "$first" "$last" "$4"
        printf '%s\t%s\t%s\n' "$mode" "$stage" measured >> "$out/coverage.tsv"
    done
done
cd "$out"
find . -type f \( -name 'coverage.tsv' -o -name 'signal-table.tsv' -o -name 'ports.json' -o -name 'activity.json' -o -name 'receipt.json' \) \
    -print0 | sort -z | xargs -0 sha256sum > results.sha256
sha256sum -c results.sha256
echo C639_RESIDUAL_ARCHIVED_WINDOWS_SCANNED
