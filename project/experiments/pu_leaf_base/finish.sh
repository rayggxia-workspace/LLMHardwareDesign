#!/usr/bin/env bash
set -euo pipefail
source_root=$1
candidate=$2
cpus=${SLURM_CPUS_PER_TASK:?}
root=$(dirname "$candidate")
tmp=$root/finish-tmp-$SLURM_JOB_ID
mkdir -p "$tmp"
srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu --pwd "$source_root" \
    --env "TMPDIR=$tmp,OMP_NUM_THREADS=$cpus,QT_QPA_PLATFORM=offscreen" \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
    bash -c '
        set -euo pipefail
        source /OpenROAD-flow-scripts/env.sh
        dst=$1
        cpu=$2
        src=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[\"cts_checkpoint\"])" "$dst/inputs.json")
        routed=$(find "$dst/flow/results" -name 5_route.odb)
        test -f "$routed"
        reference=$(find "$src/flow/results" -name 1_synth_lec.v)
        test -f "$reference"
        cp -p "$reference" "$(dirname "$routed")/1_synth_lec.v"
        cmd=(make -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=$dst/config.mk" "WORK_HOME=$dst/flow" "NUM_CORES=$cpu")
        "${cmd[@]}" do-finish > "$dst/do-finish-retry.log" 2>&1
        "${cmd[@]}" do-gds > "$dst/do-gds.log" 2>&1
        ' bash "$candidate" "$cpus"
exec bash "$source_root/project/experiments/pu_leaf_base/audit.sh" "$source_root" "$candidate"
