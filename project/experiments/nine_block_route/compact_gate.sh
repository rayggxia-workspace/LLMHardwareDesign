#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
case_file="$(realpath "${1:?}")"
case "${SLURM_ARRAY_TASK_ID:?}" in
    0) kind=P; eco=eco-98042-0 ;;
    1) kind=C; eco=eco-98057-1 ;;
    2) kind=U; eco=eco-98057-2 ;;
    *) exit 2 ;;
esac
out="$base/compact-sta-${SLURM_ARRAY_JOB_ID}-$kind"
mkdir "$out"
cd "$out"
ln -s "$base/$eco/eco-routed.v" .
ln -s "$base/$eco/candidate.spef" .
python3 "$base/eco_load.py" "$case_file"
python3 "$base/gate_eco.py" "$kind" "$(realpath ../../..)" "$out/$kind-load.tsv"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$out/sta-1.tcl" > sta-1.log 2>&1
