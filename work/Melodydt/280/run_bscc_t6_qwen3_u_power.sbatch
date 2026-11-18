#!/usr/bin/env bash
#SBATCH --job-name=mdt-280upower
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
        bash "$bundle/run_bscc_t6_qwen3_u_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$@"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/power-$3
scope=$5
physical=$root/${6:?physical path}
case "$scope" in
    e) top=e_s32_ap64 ;;
    scope) top=s32_add_scope ;;
    add) top=projection_bias_e32_s128 ;;
    *) exit 2 ;;
esac
(cd "$physical" && sha256sum --quiet -c physical.sha256)
mkdir "$out"
export PYTHONPATH=$root/writer-power/frozen
python3 -B "$bundle/qwen3_u_component_power.py" "$root/component-checks/check-38792815/add.vcd" \
    "$physical/flow/results/nangate45/$top/base" "$out" "$scope" "$4"
cd "$out"
sha256sum u-power.json active/receipt.json quiet/receipt.json > results.sha256
sha256sum -c results.sha256
