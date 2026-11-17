#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmquiet
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
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_qwen3_c639_pm_quiet.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
live=$root/pm-runtime/pm-live-power-38813039
physical=$root/leaf-physical/physical-38794460
out=$bundle/quiet-$3
(cd "$live" && sha256sum --quiet -c results.sha256)
(cd "$physical" && sha256sum --quiet -c physical.sha256)
export PYTHONPATH=$root/writer-power/frozen:$root/pm-runtime
mkdir "$out"
python3 -B "$bundle/qwen3_c639_pm_quiet_pair.py" "$live" \
    "$physical/flow/results/nangate45/lc_program_store_1k/base" "$out" "$4"
cd "$out"
sha256sum "$bundle/inputs.sha256" "$live/results.sha256" "$physical/physical.sha256" \
    "$root/writer-power/frozen/gate_power_300.py" "$root/pm-runtime/qwen3_c639_pm_runtime_audit.py" \
    pm-quiet-pair.json */quiet.vcd */power/receipt.json > results.sha256
sha256sum -c results.sha256
