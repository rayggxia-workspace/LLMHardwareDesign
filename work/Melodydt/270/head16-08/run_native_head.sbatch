#!/bin/bash
#SBATCH --job-name=zny-head-rtl
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:45:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
variant=$1
mode=$2
original=/public/home/yuzelu/project-circuit/issue260-product-result-vocab-xlXs1bpB
archive="$original/source.tar"
assets="$original/typed-vocab-105394"
launch=project/experiments/block_local_native/run_native_typed_vocabulary.sh
audit=project/experiments/block_local_native/audit_native_product_vocabulary.py
printf '%s  %s\n' \
 12a2da914a45754484c04297947ba996206ea96e41057b2a4c4f3abd1906554a "$archive" \
 17098a808c6dfa893170fc9244402b8db4d85569cb502e59ece0a2e3d64716c9 "$assets/proof.sha256" \
 b607a8098a45921e6c89dfc666aaac3ff6d2cd47b0e5903e2b7bcbaee8f50a85 "$original/vocabulary-addon.tar.gz" \
 cb2b14f19f28231a7bf1dc318953d4fca42610685ddd4d76da247688405c6062 "$original/product-addon-v2.tar.gz" \
 52d5ee90a040a56b7f487236d8a7e3d1ddd99717c3e914adc50e1108b5e8d98c "$original/source/$launch" \
 67686e0d03a467ec4fc3e2f3eb0228ba733fe1cf9c2b5d1bbd2e63e6810df3d1 "$original/source/$audit" | sha256sum -c
(cd "$assets"; grep '  generated/' proof.sha256 | sha256sum --quiet -c -)
work="$PWD/run-$SLURM_JOB_ID"
mkdir -p "$work/source"
for f in source.tar algo1.tar vocabulary-addon.tar.gz product-addon-v2.tar.gz; do ln -s "$original/$f" "$work/$f"; done
ln -s "$assets" "$work/assets"
tar -xf "$archive" -C "$work/source" --no-same-owner --no-same-permissions
tar -xzf "$original/vocabulary-addon.tar.gz" -C "$work/source" --no-same-owner --no-same-permissions
tar -xzf "$original/product-addon-v2.tar.gz" -C "$work/source" --no-same-owner --no-same-permissions
cp "$original/source/$launch" "$work/source/$launch"
cp "$original/source/$audit" "$work/source/$audit"
bash repair_native_head.sh bootstrap "$work"
sha256sum repair_native_head.sh "$work/source/project/experiments/block_local_native/audit_algo1_vocabulary.py" > "$work/postprocessing.sha256"
(
 cd "$original/source"
 sha256sum -c <<'KV'
47f82f592785e1db694380454b2c6bec333fe0b7b98a9ff92e2b92341d45c744  project/rtl/block_local_native/native_kv_request_terminal.sv
d22cd0a2190b19cc13e903804cd2eadffb6fe46d6b50b50794827a8bf3a2a021  project/rtl/block_local_native/native_kv_store_commit.sv
a4cca9953869f89185ac02008c16bf437b8719a3624d94250979b0b48f946cdc  project/rtl/mother_control_native/native_kv_phase_barrier.sv
KV
 cp --parents project/rtl/block_local_native/{native_kv_request_terminal,native_kv_store_commit}.sv \
  project/rtl/mother_control_native/native_kv_phase_barrier.sv "$work/source"
)
python3 -B prepare_native_head.py "$work/source" "$work/source/$launch" "$variant" "$mode"
if [[ ${HEAD_READ_PIPELINE:-0} == 1 ]]; then
 python3 -B prepare_head_read.py "$work/source"
fi
bash -n "$work/source/$launch"
sha256sum prepare_native_head.py run_native_head.sbatch "$work/source/$launch" "$work/source/$audit" \
 "$work/source/project/experiments/shared_x_control/rtl/p_native_weight_overlap_candidate.sv" > "$work/source.sha256"
sha256sum "$work/source/project/rtl/block_local_native/"{s128_vocabulary_retire,s128_vocabulary_tile_consumer,native_vocabulary_product_terminal}.sv >> "$work/source.sha256"
if [[ ${HEAD_READ_PIPELINE:-0} == 1 ]]; then
 sha256sum prepare_head_read.py run_head_read.sbatch >> "$work/source.sha256"
fi
capture=/public/home/yuzelu/project-circuit/issue260-predecessor-hidden-BrFwABWO/capture-104059
printf '%s  %s\n' 8dcbfe61988e658775b459233f0bd8dd93d4097db1394ce69e82a6c444f85d3e "$capture/final-hidden.json" | sha256sum -c
srun --exact -n1 -c"$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SLURM_SUBMIT_DIR=$PWD" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$work/source/$launch" in-container "$work" \
 terminal-full "$capture" 8dcbfe61988e658775b459233f0bd8dd93d4097db1394ce69e82a6c444f85d3e
cd "$work/typed-vocab-$SLURM_JOB_ID"
sha256sum -c proof.sha256 > verified-proof.log
cmp "DDR-$mode/logits.hex" "$assets/generated/reference.hex"
grep -E '^HEAD_TIMING |^HEAD_ARGMAX |^NATIVE_VOCAB_INDEX_' "replay-$mode.log" > head-timing.log
sha256sum head-timing.log > head-timing.sha256
