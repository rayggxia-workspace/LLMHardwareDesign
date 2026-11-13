#!/usr/bin/env bash
set -euo pipefail
root=/public/home/yuzelu/Melodydt/LLMHardwareDesign-issue149
out=/public/home/yuzelu/Melodydt/runs/issue-149/e-smoke-20261031-01
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
date -Is
hostname
printf 'JOB_ID=%s CPUS=%s NODE=%s\n' "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$SLURM_JOB_NODELIST"
scontrol show job "$SLURM_JOB_ID" > "$out/allocation.txt"
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
printf '%s  %s\n' "$actual" "$image" > "$out/image.sha256"
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 --version; g++ --version; /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --version' > "$out/tool-versions.log" 2>&1
bash "$root/project/experiments/block_v2/remote_rtl.sh" "$root" "$out" e
date -Is
