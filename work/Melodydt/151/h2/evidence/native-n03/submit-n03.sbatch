#!/bin/bash
#SBATCH --job-name=zenanyan-w5-af
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=UNLIMITED
#SBATCH --output=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/slurm/zenanyan-w5-af-%j.out
#SBATCH --error=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/slurm/zenanyan-w5-af-%j.err
set -euo pipefail
umask 077
test -n "${SLURM_JOB_ID:?allocation required}"
test "${SLURM_CPUS_PER_TASK:?allocation required}" -ge 8
TASK_BOOTSTRAP_DIR="$(mktemp -d /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/runs/.bootstrap-XXXXXX)"
mkdir -p "$TASK_BOOTSTRAP_DIR/home" "$TASK_BOOTSTRAP_DIR/tmp" "$TASK_BOOTSTRAP_DIR/cache"
mkdir -p "$TASK_BOOTSTRAP_DIR/singularity-cache" "$TASK_BOOTSTRAP_DIR/singularity-tmp"
export SINGULARITY_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export SINGULARITY_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export APPTAINER_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export APPTAINER_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export TMPDIR="$TASK_BOOTSTRAP_DIR/tmp"
export XDG_CACHE_HOME="$TASK_BOOTSTRAP_DIR/cache"
TASK_IMAGE_SHA="$(sha256sum /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif | cut -d' ' -f1)"
printf "job=%s node=%s image_sha=%s source=7a656a3fe4a86342d24b72ebecdc524052bf86d7\n" "$SLURM_JOB_ID" "${SLURMD_NODENAME:-unverified}" "$TASK_IMAGE_SHA"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --no-home --bind /public/home/yuzelu/Melodydt:/public/home/yuzelu/Melodydt:rw --bind /public/home/yuzelu/opt:/public/home/yuzelu/opt:ro --pwd /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/input-n03 --home "$TASK_BOOTSTRAP_DIR/home" --bind "$TASK_BOOTSTRAP_DIR/tmp:/tmp:rw" --env "TMPDIR=$TASK_BOOTSTRAP_DIR/tmp,XDG_CACHE_HOME=$TASK_BOOTSTRAP_DIR/cache,OMP_NUM_THREADS=1" --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_JOB_NAME=$SLURM_JOB_NAME,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-},SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-}" /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif python3 /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/input-n03/work/Melodydt/151/h2/run_af.py --root /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/input-n03 --output /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103/runs/n03 --vectors /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af1024-ddc6b42-20261103/runs/r03/vectors --source-commit 7a656a3fe4a86342d24b72ebecdc524052bf86d7 --container-sha256 "$TASK_IMAGE_SHA"
