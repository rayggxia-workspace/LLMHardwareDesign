#!/usr/bin/env bash
#SBATCH --job-name=mdt-280dmastate
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
    sha256sum --quiet -c dma-state-inputs.sha256
    (cd c639-inputs && sha256sum --quiet -c inputs.sha256)
    chmod u+x c639-inputs/fst_scope_vcd
    unset TCL_LIBRARY TK_LIBRARY TCLLIBPATH
    exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores /public3/soft/singularity/3.7.0/bin/singularity exec --cleanenv \
      --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
      bash "$bundle/run_dma_state_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "${1:?variant}"
fi
bundle=$2
source /OpenROAD-flow-scripts/env.sh
export OMP_NUM_THREADS=12 OPENBLAS_NUM_THREADS=1
python3 -B "$bundle/dma_state_power.py" "$(dirname "$bundle")" "$bundle" "$bundle/dma-state-$3-$4" "$4"
cd "$bundle/dma-state-$3-$4"
sha256sum calibration.json */receipt.json > results.sha256
sha256sum --quiet -c results.sha256
