#!/usr/bin/env bash
#SBATCH --job-name=mdt-r6179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-r6-13e577c/r001/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-r6-13e577c
cd "$root/r001"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro --bind "$root/r001:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
python3 --version
g++ --version | head -n 1
/eda/verilator-5.042/bin/verilator --version
python3 -B project/control_r6_v0_1/run_campaign.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/r6
'
printf 'PASS %s\n' "$(date -Is)"
