#!/usr/bin/env bash
#SBATCH --job-name=mdt-280writerpair
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum -c inputs.sha256
    image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$image" \
        bash "$bundle/run_bscc_t6_c639_writer_pair.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
output=$bundle/pair-$3
physical=$root/writeback/physical-38769390/flow/results/nangate45/ffn_down_store_scope/base
input=$root/writer-active-recovered/power-38782231
export PYTHONPATH=$root/writer-power/frozen
mkdir "$output"
for mode in 0 1; do
    python3 "$bundle/measure_c639_writeback_window.py" --pair \
        "$input/mode-$mode-writer-active/ports.vcd" "$physical" "$output/mode-$mode" "$4"
done
cd "$output"
sha256sum mode-*/paired.json mode-*/*/receipt.json > results.sha256
sha256sum -c results.sha256
