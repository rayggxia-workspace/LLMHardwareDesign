#!/usr/bin/env bash
#SBATCH --job-name=mdt-lc179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1/r005/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-control-rtl-41777f1
cd "$root/r005"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
sha256sum source.tar
cat source.json
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro --bind "$root/r005:/work" --pwd /work/source \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif \
  python3 -B project/control_rtl_min_v0_1/run.py --simulator verilator --verilator /eda/verilator-5.042/bin/verilator --out /work/results
printf 'PASS %s\n' "$(date -Is)"
