#!/usr/bin/env bash
#SBATCH --job-name=mdt-r7179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/yuzelu/Melodydt/issue179-r7-0429573/r001/slurm-%j.log
set -euo pipefail
root=/public/home/yuzelu/Melodydt/issue179-r7-0429573
cd "$root/r001"
printf 'START %s host=%s job=%s cpus=%s
' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source-r001.tar
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro --bind "$root/r001:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
python3 --version
python3 -B project/control_r7_v0_1/synthesize.py \
    --yosys /usr/local/bin/yosys \
    --openroad /eda/r166-openroad-gc-cache-2eba27b2-offline01/install/bin/openroad \
    --liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib \
    --out /work/results/synthesis
'
printf 'PASS %s
' "$(date -Is)"
