#!/bin/bash
#SBATCH --job-name=zny-ffn-mprobe
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:50:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root=/public/home/yuzelu/project-circuit
archive="$root/issue260-decode638-live-product-ffn-repeat5-SR6Qffhj/source.tar"
printf '%s  %s\n' 8294abc3b8da18f22db091627353b68cdd1498ab2e32c1293a8b0abd56b4a5da "$archive" | sha256sum -c
work="$PWD/run-$SLURM_JOB_ID"
mkdir -p "$work/source"
ln -s "$archive" "$work/source.tar"
tar -xf "$archive" -C "$work/source" --no-same-owner --no-same-permissions
python3 -B ../prepare_native_probe.py "$work/source"
runner="$work/source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh"
bash -n "$runner"
sha256sum "$archive" ../prepare_native_probe.py run_native_probe.sbatch "$runner" \
 "$work/source/project/rtl/w8a16_v1/m_native_leaf_s32.sv" > "$work/source.sha256"
srun --exact -n1 -c"$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,FORCE_SECOND_FFN_REARM=1" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash \
 "$runner" "$work" "$root/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952" history-final-product-ffn-repeat 636 2
cd "$work/replay-$SLURM_JOB_ID"
sha256sum -c proof.sha256 > verified-proof.log
grep '^M_WEIGHT ' replay-0.log > m-weight-0.tsv
grep '^M_WEIGHT ' replay-1.log > m-weight-1.tsv
sha256sum m-weight-0.tsv m-weight-1.tsv > m-weight.sha256
