#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
id="${1:?}"; index="${2:?}"; kind="${3:?}"
out="$base/eco-$id-$index"
cd "$out"
python3 "$base/gate_eco.py" "$kind" "$(realpath ../../..)" "$base/$kind-load.tsv"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu
         --env "GATE_DB=$out/eco-routed.odb,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/gate_eco.tcl" > extraction.log 2>&1
for stress in 0 1; do
    "${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$out/sta-$stress.tcl" > "sta-$stress.log" 2>&1
done
