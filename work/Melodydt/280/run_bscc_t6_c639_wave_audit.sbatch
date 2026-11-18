#!/usr/bin/env bash
#SBATCH --job-name=mdt-280waveaudit
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

legacy=/public/home/yuzelu
original=$legacy/Melodydt/runs/issue-280/c639-g32-gate-01/c639-g32-116937/replay-116937
if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    root=$(dirname "$bundle")
    cd "$bundle"
    sha256sum -c bundle.sha256
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$root" --bind "$root/wide/sourcefs:$legacy:ro" \
        "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_c639_wave_audit.sbatch" inside "$bundle" "$SLURM_JOB_ID"
fi

bundle=$2
root=$(dirname "$bundle")
out=$bundle/audit-$3
run=$root/wide/wide-38772137/replay-38772137
sources=$root/wide/wide-38772137/source/project/experiments/block_local_native
helper=$root/writer-power/frozen
scope=TOP/test_native_decode638_product_replay/typed_dma
mkdir "$out" "$out/audit-input"
ln -s "$original/generated" "$out/audit-input/generated"
test -s "$run/ddr-audit.json"
cp "$run/ddr-audit.json" "$out/"
for mode in 0 1; do
    ln -s "$run/replay-$mode.log" "$out/audit-input/"
    digest=$(awk -v mode="$mode" '$1==mode {print $2}' "$root/wide/read-transactions.sha256")
    printf '%s  %s\n' "$digest" "$run/DDR-$mode/transactions.tsv" | sha256sum -c -
    for item in write-transactions.tsv activation-transactions.tsv committed-kv.bin; do
        cmp "$original/DDR-$mode/$item" "$run/DDR-$mode/$item"
    done
    grep -q '^PASS q projection ' "$run/replay-$mode.log"
    grep -q '^HISTORY_KV_COMPLETE ' "$run/replay-$mode.log"
done
python3 -B "$sources/audit_decode638_qkv_page.py" "$out/audit-input" > "$out/qkv-terminal-audit.json"
sha256sum "$sources/audit_decode638_qkv_page.py" "$original/generated/program.json" > "$out/audit-inputs.sha256"

for mode in 0 1; do
    for stage in gate-up down writer-active; do
        fst=$run/DDR-$mode/ffn-$stage.fst
        sample=$out/mode-$mode-$stage
        mkdir "$sample"
        "$helper/fst_scope_table" "$fst" > "$sample/signal-table.tsv"
        awk -F '\t' '$1=="var" && $2 ~ /typed_dma\/dma$/ && $3 ~ /^c_rsp_data/ && $4==6144 {found=1} END{exit !found}' "$sample/signal-table.tsv"
        "$helper/fst_scope_vcd" "$fst" "$sample/dma.vcd" "$scope" > "$sample/extract.log"
        python3 -B "$bundle/read_c639_dma_activity.py" "$sample/dma.vcd" "$scope" > "$sample/activity.json"
    done
done
cd "$out"
sha256sum qkv-terminal-audit.json ddr-audit.json audit-inputs.sha256 mode-*/{signal-table.tsv,activity.json} > audit-results.sha256
sha256sum -c audit-results.sha256
cd "$run"
test ! -e wide-results.sha256
sha256sum "$out/audit-results.sha256" "$out/qkv-terminal-audit.json" ddr-audit.json \
    DDR-*/{ffn-*.fst,transactions.tsv,write-transactions.tsv,activation-transactions.tsv,committed-kv.bin} > "$out/wide-results.sha256"
sha256sum --quiet -c "$out/wide-results.sha256"
cp "$out/wide-results.sha256" wide-results.sha256
echo C639_WIDE_OUTPUTS_AND_READ_ACTIVITY_VERIFIED
