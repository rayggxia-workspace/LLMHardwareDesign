#!/usr/bin/env bash
#SBATCH --job-name=zny-qwenedge
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:45:00
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum -c source.sha256

verify_replay() (
    cd "$1"
    baseline=$2
    run=$3
    output=$4
    awk '{ sub(/^.*\/DDR-/, "DDR-", $2) } $2 ~ /^DDR-[01]\/(transactions\.tsv|write-transactions\.tsv|activation-transactions\.tsv|committed-kv\.bin)$/ { print $1 "  " $2 }' \
        "$baseline/proof.sha256" > "$output/expected-ddr.sha256"
    test "$(wc -l < "$output/expected-ddr.sha256")" -eq 8
    sha256sum -c "$output/expected-ddr.sha256"
    sha256sum -c prepared.sha256
    for mode in 0 1; do
        python3 -B "$run/instrument_qwen_105530.py" audit "replay-$mode.log" "$baseline/replay-$mode.log" > "$output/edges-$mode.json"
        grep '^QWEN_EDGE ' "replay-$mode.log" > "$output/edges-$mode.log"
    done
    sha256sum "$output/expected-ddr.sha256" "$1/prepared.sha256" "$output"/edges-{0,1}.{json,log} \
        "$1"/replay-{0,1}.log "$1/ddr-audit.json" "$(dirname "$1")/instrumented.sha256" > "$output/marker-proof.sha256"
    sha256sum -c "$output/marker-proof.sha256"
)

root=/public/home/yuzelu/project-circuit
archive=$root/issue260-decode638-live-product-next-rms-u8Z2olTH
baseline=$archive/replay-105530
linked=$root/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '%s  %s\n' \
    e6833398029d6348699370a6fb8630968792849c0b83a4e8974812a53cae3b32 "$archive/source.tar" \
    afa825d6f1d3f549adf5a8cfb021c85e4cb428b00ff06cf46acbd44f2c298ee9 "$baseline/proof.sha256" \
    685e11dbc0c7ede0b2802bc52babf8be84f708cf22aded03a65d65b2e4bdf157 "$baseline/tools.sha256" \
    49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a "$image" | sha256sum -c -
sha256sum -c "$baseline/tools.sha256"

run=$PWD
pair_predictions=
if [[ ${1:-} == --pair ]]; then
    pair_predictions=$(realpath "${2:?sealed three-record prediction directory required}")
    (cd "$pair_predictions" && sha256sum -c prediction.sha256)
fi
if [[ ${1:-} == --verify ]]; then
    prior=$(realpath "${2:?existing instrumented replay directory required}")
    verify_replay "$prior" "$baseline" "$run" "$run"
    exit
fi
replay=$run/replay-$SLURM_JOB_ID
mkdir source "$replay"
tar xf "$archive/source.tar" -C source
cp "$archive/source.tar" source.tar
cp -R "$baseline/generated" "$replay/generated"
(
    cd "$replay"
    awk '$2 ~ /^generated\// { print }' "$baseline/proof.sha256" > prepared.sha256
    sha256sum -c prepared.sha256
)
if [[ -n "$pair_predictions" ]]; then
    python3 -B instrument_qwen_105530_pair.py "$run/source"
else
    python3 -B instrument_qwen_105530.py patch "$run/source"
fi
runner=$run/source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh
top=$run/source/project/experiments/block_local_native/test_native_decode638_product_replay.sv
if [[ -n "$pair_predictions" ]]; then
    python3 -B audit_qwen_105530_pair.py prepare-runner "$runner"
fi
bash -n "$runner"
sha256sum "$runner" "$top" > instrumented.sha256
srun --exact -n1 -c"$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
    --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" \
    "$image" bash "$runner" "$run" "$linked" history-final-product-ffn-next-rms 636 2

if [[ -n "$pair_predictions" ]]; then
    python3 -B audit_qwen_105530_pair.py compare "$pair_predictions" "$replay" "$baseline" > "$replay/pair-audit.json"
    sha256sum source.sha256 instrumented.sha256 "$replay"/{prepared.sha256,build.log,tools.sha256,pair-audit.json,replay-0.log,replay-1.log,DDR-0/transactions.tsv,DDR-1/transactions.tsv} > output.sha256
    sha256sum -c output.sha256
    python3 -B audit_qwen_105530_pair.py require-match "$replay/pair-audit.json"
else
    verify_replay "$replay" "$baseline" "$run" "$replay"
fi
