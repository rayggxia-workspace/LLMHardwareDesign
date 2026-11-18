#!/usr/bin/env bash
#SBATCH --job-name=mdt-280dmawave
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

legacy=/public/home/yuzelu
original=$legacy/Melodydt/runs/issue-280/c639-g32-gate-01/c639-g32-116937
if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    profile=${1:-writer}
    [[ $profile == writer || $profile == m-exec ]]
    sha256sum -c bundle.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" --bind "$bundle/sourcefs:$legacy:ro" \
        "$opt/orfs-current-repacked.rootfs" bash "$bundle/run_bscc_t6_c639_wide.sbatch" inside \
        "$bundle" "$opt" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$profile"
fi

bundle=$2
opt=$3
export SLURM_JOB_ID=$4 SLURM_CPUS_PER_TASK=$5
export FORCE_SECOND_FFN_REARM=1
export C639_GENERATED=$original/replay-116937/generated
export VERILATOR_ROOT=$opt/verilator-5.042/share/verilator
export C639_VERILATOR=$opt/verilator-5.042/bin/verilator
run=$bundle/wide-$SLURM_JOB_ID
profile=$6
mkdir "$run"
cp -a "$original/"{source,source.tar,activity-0.txt,activity-1.txt} "$run/"
runner=$run/source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh
m_leaf=$run/source/project/rtl/w8a16_v1/m_native_leaf_s32.sv
if [[ $profile == m-exec ]]; then
    python3 -B "$bundle/prepare_c639_m_exec_ready.py" "$m_leaf" "$run/exec-ready-guard.v"
fi
python3 -B "$bundle/prepare_bscc_t6_c639_wide.py" "$runner" "$profile"
bash -n "$runner"
sha256sum "$runner" "$(dirname "$runner")/"{test_native_decode638_product_replay.sv,c639_activity_driver.cpp} \
    "$C639_VERILATOR" "$C639_GENERATED/program.json" "$m_leaf" > "$run/inputs.sha256"
bash "$runner" "$run" unused-prepared history-final-product-ffn-repeat 636 2
out=$run/replay-$SLURM_JOB_ID
(cd "$out" && sha256sum --quiet -c proof.sha256)
for mode in 0 1; do
    for item in write-transactions.tsv activation-transactions.tsv committed-kv.bin; do
        cmp "$original/replay-116937/DDR-$mode/$item" "$out/DDR-$mode/$item"
    done
    digest=$(awk -v mode="$mode" '$1==mode {print $2}' "$bundle/read-transactions.sha256")
    printf '%s  %s\n' "$digest" "$out/DDR-$mode/transactions.tsv" | sha256sum -c -
    for phase in gate-up down writer-active; do
        "$bundle/../writer-power/frozen/fst_scope_table" "$out/DDR-$mode/ffn-$phase.fst" > "$out/DDR-$mode/ffn-$phase-signals.tsv"
        awk -F '\t' '$1=="var" && $2 ~ /typed_dma\/dma$/ && $3 ~ /^c_rsp_data/ && $4==6144 {found=1} END{exit !found}' \
            "$out/DDR-$mode/ffn-$phase-signals.tsv"
    done
done
cd "$out"
sha256sum proof.sha256 "$run/inputs.sha256" DDR-*/ffn-*.fst DDR-*/ffn-*-signals.tsv > wide-results.sha256
sha256sum -c wide-results.sha256
echo C639_6144_BIT_RETURN_CAPTURE_PASS
