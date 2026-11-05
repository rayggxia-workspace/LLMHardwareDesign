#!/usr/bin/env bash
#SBATCH --job-name=mdt-a2g179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root=/public/home/yuzelu/Melodydt/issue179-a2g-2e36492
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source.tar
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$PWD:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
platform=/OpenROAD-flow-scripts/flow/platforms/nangate45
openroad=/eda/r166-openroad-gc-cache-2eba27b2-offline01/install/bin/openroad
verilator=/eda/verilator-5.042/bin/verilator
export SLURM_CPUS_PER_TASK=4
(
  python3 -B project/control_r4_v0_1/check_contract.py &&
  python3 -B project/control_p_compute_v0_1/run_a2.py --silu --verilator "$verilator" --out /work/results/silu &&
  python3 -B project/control_p_compute_v0_1/run_a2.py --verilator "$verilator" --out /work/results/dot &&
  python3 -B project/control_r6_v0_1/run_campaign.py --verilator "$verilator" --out /work/results/r6 &&
  python3 -B project/control_r4_v0_1/run_reset.py --verilator "$verilator" --out /work/results/reset
) &
functional_pid=$!
timing_rc=0
python3 -B project/control_p_compute_v0_1/silu_mapping.py --yosys /usr/local/bin/yosys \
  --openroad "$openroad" --liberty "$platform/lib/NangateOpenCellLibrary_typical.lib" --out /work/results/mapped &&
python3 -B project/control_timing_v0_1/close.py --yosys /usr/local/bin/yosys --openroad "$openroad" \
  --platform "$platform" --mapped /work/results/mapped --out /work/results/repair \
  --workers 2 --modules silu_mother silu_local silu_store || timing_rc=$?
functional_rc=0
wait "$functional_pid" || functional_rc=$?
printf "RESULT functional=%s timing=%s\n" "$functional_rc" "$timing_rc"
test "$functional_rc" = 0 && test "$timing_rc" = 0
'
printf 'PASS %s\n' "$(date -Is)"
