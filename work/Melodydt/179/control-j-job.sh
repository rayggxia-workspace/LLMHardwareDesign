#!/usr/bin/env bash
#SBATCH --job-name=mdt-jctrl179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root=/public/home/yuzelu/Melodydt/issue179-jc-500f630
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source.tar
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$PWD:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
verilator=/eda/verilator-5.042/bin/verilator
export SLURM_CPUS_PER_TASK=4
mkdir -p /work/results
python3 -B project/control_r4_v0_1/check_contract.py > /work/results/r4-static.json
python3 -B project/control_j_compute_v0_1/run_j.py --verilator "$verilator" --out /work/results/j
'
printf 'PASS %s\n' "$(date -Is)"
