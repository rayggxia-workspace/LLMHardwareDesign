#!/usr/bin/env bash
#SBATCH --job-name=mdt-t179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root=/public/home/yuzelu/Melodydt/issue179-timing-90cc9d8
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source.tar
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$PWD:/work" --bind /public/home/yuzelu/Melodydt/issue179-timing-90cc9d8/r001/results/mapped:/mapped:ro --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
platform=/OpenROAD-flow-scripts/flow/platforms/nangate45
openroad=/eda/r166-openroad-gc-cache-2eba27b2-offline01/install/bin/openroad
python3 -B project/control_timing_v0_1/close.py --openroad "$openroad" --platform "$platform" \
    --yosys /usr/local/bin/yosys --mapped /mapped --out /work/results/repair --workers 6
python3 -B project/control_p_compute_v0_1/run_a2.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/a2
python3 -B project/control_r6_v0_1/run_campaign.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/r6
python3 -B project/control_r4_v0_1/run_reset.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/reset
'
printf 'PASS %s\n' "$(date -Is)"
