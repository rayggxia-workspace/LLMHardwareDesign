#!/bin/bash
#SBATCH --job-name=hpy-dm173
set -eu
task_root=/public/home/yuzelu/PingyangHuang/issue-173-dram-m-fifo-20261103T114626Z
export TMPDIR="$task_root/tmp" XDG_CACHE_HOME="$task_root/cache" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
cd "$task_root/source"
mkdir -p "$task_root/home" "$task_root/container-tmp" "$task_root/container-cache"
export SINGULARITY_TMPDIR="$task_root/container-tmp" SINGULARITY_CACHEDIR="$task_root/container-cache"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sha256sum "$image" > "$task_root/image.sha256"
test "$(cut -d " " -f 1 "$task_root/image.sha256")" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --cpu-bind=cores --ntasks=1 --cpus-per-task=8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --containall --home "$task_root/home" --bind "$task_root:$task_root" --bind /public/home/yuzelu/opt/eda/verilator-5.042:/public/home/yuzelu/opt/eda/verilator-5.042:ro --pwd "$task_root/source" --env TMPDIR="$task_root/tmp",XDG_CACHE_HOME="$task_root/cache",PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=1,SLURM_JOB_ID="$SLURM_JOB_ID",SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" "$image" python3 -B project/experiments/dram_m_fifo/run.py --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --jobs 8 --out "$task_root/results"
