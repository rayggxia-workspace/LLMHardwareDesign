#!/usr/bin/env bash
set -euo pipefail
root=$1
src=$root/source
gate=${2:-}
extra=()
case "${SLURM_ARRAY_TASK_ID:?}" in
    0) kind=3 ;;
    1) kind=-1 ;;
    2) kind=3; extra=(P) ;;
    3) kind=-1; extra=(U) ;;
    *) exit 2 ;;
esac
run=$root/fixture-$SLURM_ARRAY_TASK_ID
python3 -B "$src/project/experiments/pu_leaf_base/control_replay.py" "$src" "$run" "${extra[@]}"
if [[ -n "$gate" ]]; then
    [[ ${#extra[@]} == 1 && -f "$gate" ]]
    cpus=${SLURM_CPUS_PER_TASK:?}
    sha256sum "$gate" > "$run/gate-sha256.txt"
    suffix=""
    if [[ ${PU_INSTRUCTION_BITS:-128} == 64 ]]; then suffix=_64; fi
    cp "$gate" "$run/design/pu_${extra[0],,}_controlled${suffix}.sv"
    srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
        --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
        bash -c 'source /OpenROAD-flow-scripts/env.sh; yosys -Q -p "read_liberty -ignore_miss_func -ignore_miss_dir $1; write_verilog -noattr $2"' \
        bash /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib "$run/design/pu_cells.sv" \
        > "$run/gate-model.log"
fi
exec srun --exact --ntasks=1 --cpus-per-task="${SLURM_CPUS_PER_TASK:?}" --cpu-bind=cores \
    bash "$run/design/run.sh" "$run" "$run/results" "$kind"
