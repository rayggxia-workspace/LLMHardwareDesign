#!/usr/bin/env bash
#SBATCH --job-name=mdt-280conv4
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
    sha256sum --quiet -c conv4-inputs.sha256
    unset TCL_LIBRARY TK_LIBRARY TCLLIBPATH
    exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores /public3/soft/singularity/3.7.0/bin/singularity exec --cleanenv \
      --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
      bash "$bundle/run_conv4.sbatch" inside "$bundle" "$SLURM_JOB_ID"
fi
bundle=$2
source /OpenROAD-flow-scripts/env.sh
export OMP_NUM_THREADS=12 OPENBLAS_NUM_THREADS=1
python3 -B "$bundle/calibrate_conv4.py" "$bundle" "$bundle/conv4-$3"
cd "$bundle/conv4-$3"
sha256sum calibration.json mapped.v > results.sha256
sha256sum --quiet -c results.sha256
