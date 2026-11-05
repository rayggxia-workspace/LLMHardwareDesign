#!/usr/bin/env bash
#SBATCH --job-name=mdt-r4179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-r4-real-ecd6f49/r003/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-r4-real-ecd6f49
cd "$root/r003"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
cat source.json
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro --bind "$root/r003:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
python3 --version
g++ --version | head -n 1
/eda/verilator-5.042/bin/verilator --version
python3 -B project/control_r4_v0_1/run_real_dma.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/real_dma
'
printf 'PASS %s\n' "$(date -Is)"
