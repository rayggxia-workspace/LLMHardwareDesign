#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pinpower
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
    sha256sum --quiet -c pin-inputs.sha256
    unset TCL_LIBRARY TK_LIBRARY TCLLIBPATH
    exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores /public3/soft/singularity/3.7.0/bin/singularity exec --cleanenv \
      --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
      bash "$bundle/run_retained_pins.sbatch" inside "$bundle" "$SLURM_JOB_ID" "${1:?source}" "${2:?kind}"
fi
bundle=$2
source /OpenROAD-flow-scripts/env.sh
export OMP_NUM_THREADS=12 OPENBLAS_NUM_THREADS=1
python3 -B "$bundle/calibrate_retained_pins.py" "$4" "$bundle/pins-$3-$5" "$5"
cd "$bundle/pins-$3-$5"
sha256sum calibration.json mapped-graph.json */power.log > results.sha256
sha256sum --quiet -c results.sha256
