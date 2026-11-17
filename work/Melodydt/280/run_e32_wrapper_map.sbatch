#!/usr/bin/env bash
#SBATCH --job-name=mdt-280e32-map
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} != inside ]]; then
  bundle=${SLURM_SUBMIT_DIR:?}
  cd "$bundle"
  sha256sum --quiet -c inputs.sha256
  set +u
  source /public3/soft/modules/module.sh
  module load singularity/3.7.0
  set -u
  exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" bash "$bundle/run_e32_wrapper_map.sbatch" inside "$bundle" "$SLURM_JOB_ID"
fi
source /OpenROAD-flow-scripts/env.sh
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
bundle=$2
out=$bundle/map-$3
yosys -V > "$bundle/yosys-$3.txt"
sha256sum "$(command -v yosys)" > "$bundle/yosys-$3.sha256"
python3 -B "$bundle/map_e32_wrappers.py" "$bundle" "$out"
cd "$out"
sha256sum summary.json */receipt.json */mapped.v */mapped.json */map.log > results.sha256
sha256sum --quiet -c results.sha256
