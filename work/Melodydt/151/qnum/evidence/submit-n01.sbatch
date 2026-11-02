#!/bin/bash
#SBATCH --job-name=zenanyan-qnum
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/slurm/zenanyan-qnum-%j.out
#SBATCH --error=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/slurm/zenanyan-qnum-%j.err
set -euo pipefail
umask 077
test -n "${SLURM_JOB_ID:?allocation required}"
test "${SLURM_CPUS_PER_TASK:?allocation required}" -ge 8
TASK_BOOTSTRAP_DIR="$(mktemp -d /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/runs/.bootstrap-XXXXXX)"
mkdir -p "$TASK_BOOTSTRAP_DIR/home" "$TASK_BOOTSTRAP_DIR/tmp" "$TASK_BOOTSTRAP_DIR/cache"
mkdir -p "$TASK_BOOTSTRAP_DIR/singularity-cache" "$TASK_BOOTSTRAP_DIR/singularity-tmp"
export SINGULARITY_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export SINGULARITY_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export APPTAINER_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export APPTAINER_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export TMPDIR="$TASK_BOOTSTRAP_DIR/tmp"
export XDG_CACHE_HOME="$TASK_BOOTSTRAP_DIR/cache"
TASK_IMAGE_SHA="$(sha256sum /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif | cut -d' ' -f1)"
printf "job=%s node=%s image_sha=%s source=d0c40f5772466b4c3907bc7a2273c6adfd24ef6c\n" "$SLURM_JOB_ID" "${SLURMD_NODENAME:-unverified}" "$TASK_IMAGE_SHA"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --no-home --bind /public/home/yuzelu/Melodydt:/public/home/yuzelu/Melodydt:rw --bind /public/home/yuzelu/opt:/public/home/yuzelu/opt:ro --pwd /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/input-n01 --home "$TASK_BOOTSTRAP_DIR/home" --bind "$TASK_BOOTSTRAP_DIR/tmp:/tmp:rw" --env "TMPDIR=$TASK_BOOTSTRAP_DIR/tmp,XDG_CACHE_HOME=$TASK_BOOTSTRAP_DIR/cache,OMP_NUM_THREADS=1" --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_JOB_NAME=$SLURM_JOB_NAME,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-},SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-}" /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif python3 /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/input-n01/work/Melodydt/151/qnum/run_qnum_job.py --root /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/input-n01 --dataset /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/data01 --output /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/qwen-numeric-71c819c-20261102/runs/n01 --source-commit d0c40f5772466b4c3907bc7a2273c6adfd24ef6c --container-sha256 "$TASK_IMAGE_SHA"
