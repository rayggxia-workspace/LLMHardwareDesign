#!/bin/bash
# Generated only; no submission was performed.
#SBATCH --job-name=zenanyan-a8-all
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/slurm/zenanyan-a8-all-%j.out
#SBATCH --error=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/slurm/zenanyan-a8-all-%j.err
set -euo pipefail
umask 077
# Slurm log directory/root/runner/contracts must already exist before sbatch.
test -n "${SLURM_JOB_ID:?allocation required}"
test "${SLURM_NTASKS:-1}" -eq 1
test "${SLURM_CPUS_PER_TASK:?CPU allocation required}" -ge 8
TASK_BOOTSTRAP_DIR="$(mktemp -d /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/runs/.bootstrap-XXXXXX)"
mkdir -p "$TASK_BOOTSTRAP_DIR/home" "$TASK_BOOTSTRAP_DIR/tmp" "$TASK_BOOTSTRAP_DIR/cache"
mkdir -p "$TASK_BOOTSTRAP_DIR/singularity-cache" "$TASK_BOOTSTRAP_DIR/singularity-tmp"
export SINGULARITY_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export SINGULARITY_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export APPTAINER_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"
export APPTAINER_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"
export TMPDIR="$TASK_BOOTSTRAP_DIR/tmp"
export XDG_CACHE_HOME="$TASK_BOOTSTRAP_DIR/cache"
/public/software/singularity-ce-4.3.4/bin/singularity --version
# Hash1.5GB image only here in allocated job, never on login preflight.
TASK_IMAGE_SHA="$(sha256sum /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif | cut -d' ' -f1)"
printf "job=%s node=%s image_sha=%s\n" "$SLURM_JOB_ID" "${SLURMD_NODENAME:-unverified}" "$TASK_IMAGE_SHA"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --no-home --bind /public/home/yuzelu/Melodydt:/public/home/yuzelu/Melodydt:rw --bind /public/home/yuzelu/opt:/public/home/yuzelu/opt:ro --pwd /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/input-r02 \
  --bind "$TASK_BOOTSTRAP_DIR/tmp:/tmp:rw" \
  --env "HOME=$TASK_BOOTSTRAP_DIR/home,TMPDIR=$TASK_BOOTSTRAP_DIR/tmp,XDG_CACHE_HOME=$TASK_BOOTSTRAP_DIR/cache" \
  --env "OMP_NUM_THREADS=1,VERILATOR_ROOT=/public/home/yuzelu/opt/eda/verilator-5.042" \
  --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_JOB_NAME=$SLURM_JOB_NAME,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SLURM_NTASKS=${SLURM_NTASKS:-1}" \
  --env "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-},SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-},SLURM_JOB_END_TIME=${SLURM_JOB_END_TIME:-}" \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif python3 /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/input-r02/work/Melodydt/151/run_a8_verilator.py --root /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/input-r02 --output /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/runs/r02 --contract /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/input-r02/work/Melodydt/151/a8-verilator-baseline-contract.json --suite all --name-initials zenanyan --source-ref 1d722477564e14f7dc93e39ce8e28b8e2d150cb0 --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --build-jobs 8 --node-class c64 --job-wall-minutes 30 --container-image /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif --a8-contract /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/input-r02/work/Melodydt/151/a8-verilator-profile-contract.json --container-sha256 "$TASK_IMAGE_SHA"
