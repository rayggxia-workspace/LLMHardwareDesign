#!/usr/bin/env bash
#SBATCH --job-name=mdt-lc179p
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-control-profiles-2e6d211/r001/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-control-profiles-2e6d211
cd "$root/r001"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
sha256sum source.tar
cat source.json
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro --bind "$root/r001:/work" --pwd /work/source \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
mkdir -p /work/results
python3 --version
g++ --version | head -n 1
/eda/verilator-5.042/bin/verilator --version
python3 -B project/control_profiles_v0_1/run_profiles.py --out /work/results/profiles
'
printf 'PASS %s\n' "$(date -Is)"
