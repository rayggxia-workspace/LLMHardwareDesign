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
python3 -B instrument_qwen_105530.py patch "$run/source"
runner=$run/source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh
top=$run/source/project/experiments/block_local_native/test_native_decode638_product_replay.sv
bash -n "$runner"
sha256sum "$runner" "$top" > instrumented.sha256
srun --exact -n1 -c"$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
    --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" \
    "$image" bash "$runner" "$run" "$linked" history-final-product-ffn-next-rms 636 2

cd "$replay"
awk '{ sub(/^.*\/DDR-/, "DDR-", $2) } $2 ~ /^DDR-[01]\/(transactions\.tsv|write-transactions\.tsv|activation-transactions\.tsv|committed-kv\.bin)$/ { print }' \
    "$baseline/proof.sha256" > expected-ddr.sha256
test "$(wc -l < expected-ddr.sha256)" -eq 8
sha256sum -c expected-ddr.sha256
sha256sum -c prepared.sha256
for mode in 0 1; do
    python3 -B "$run/instrument_qwen_105530.py" audit "replay-$mode.log" "$baseline/replay-$mode.log" > "edges-$mode.json"
    grep '^QWEN_EDGE ' "replay-$mode.log" > "edges-$mode.log"
done
sha256sum expected-ddr.sha256 prepared.sha256 edges-{0,1}.{json,log} replay-{0,1}.log ddr-audit.json \
    "$run/instrumented.sha256" > marker-proof.sha256
