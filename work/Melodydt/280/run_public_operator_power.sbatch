#!/usr/bin/env bash
#SBATCH --job-name=mdt-280op-pwr
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
    exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores singularity exec --cleanenv \
        --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_public_operator_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$@"
fi
bundle=$2
job=$3
shift 3
source /OpenROAD-flow-scripts/env.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
python3 -B "$bundle/calibrate_public_operators.py" "$(dirname "$bundle")" "$bundle" "$bundle/operator-$job" "$@"
cd "$bundle/operator-$job"
sha256sum calibration.json build.log sample-*/receipt.json > results.sha256
sha256sum --quiet -c results.sha256
