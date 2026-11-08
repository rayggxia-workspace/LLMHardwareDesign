#!/usr/bin/env bash
#SBATCH --job-name=mdt-r736sta179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root="$(dirname "$PWD")"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source.tar
mkdir -p "$root/container-cache" "$root/tmp"
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$PWD:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
platform=/OpenROAD-flow-scripts/flow/platforms/nangate45
openroad=/eda/r166-openroad-gc-cache-2eba27b2-offline01/install/bin/openroad
mkdir -p /work/results
for profile in u j c common; do
  (
    mapped="/work/results/$profile/mapped"
    repair="/work/results/$profile/repair"
    if [ "$profile" = common ]; then
      modules=(extended_sink raw32_adapter f_cohort6)
    else
      modules=("${profile}_mother" "${profile}_source" "${profile}_compute")
    fi
    python3 -B project/control_r736_v0_1/map_controls.py "$profile" --yosys /usr/local/bin/yosys \
      --openroad "$openroad" --liberty "$platform/lib/NangateOpenCellLibrary_typical.lib" --out "$mapped" &&
    python3 -B project/control_timing_v0_1/close.py --yosys /usr/local/bin/yosys \
      --openroad "$openroad" --platform "$platform" --mapped "$mapped" --out "$repair" \
      --workers 3 --modules "${modules[@]}"
  ) &
  pids+=("$!")
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
'
printf 'PASS %s\n' "$(date -Is)"
