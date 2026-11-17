#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmfetch
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
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
        bash "$bundle/run_bscc_t6_qwen3_c639_pm_runtime.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

bundle=$2
root=$(dirname "$bundle")
replay=$root/m-product/wide-38792112/replay-38792112
converter=$root/writer-power/frozen/fst_scope_vcd
activity=$root/control-activity/activity-38796363
out=$bundle/pm-runtime-$3
(cd "$replay" && sha256sum --quiet -c wide-results.sha256)
(cd "$activity" && sha256sum --quiet -c results.sha256)
mkdir "$out"
python3 -B "$bundle/qwen3_c639_pm_runtime_audit.py" "$replay" "$converter" \
    "$activity/control-activity.json" "$out" --workers "$4"
cd "$out"
sha256sum "$bundle/inputs.sha256" "$replay/wide-results.sha256" "$activity/results.sha256" \
    pm-runtime-audit.json > results.sha256
sha256sum -c results.sha256
