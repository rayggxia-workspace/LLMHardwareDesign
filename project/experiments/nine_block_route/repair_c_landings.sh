#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
candidate="$(realpath eco-98057-1)"
proj="$(realpath ../..)"
accepted="$proj/issue-188-ucf16/accepted-ucf16-01/C16"
original="$proj/issue-188-ucf16/pnr-21/run-97675-c-skew2-post2/flow/results/nangate45/block_c16/base"
run="$base/eco-${SLURM_JOB_ID:?}-1"
mkdir "$run"
cd "$run"
python3 "$base/find_landing_repairs.py" "$original/sram-landing-patches.tsv" "$accepted/6_final.def" "$candidate/eco-routed.def" repairs.tsv
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu)
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
"${runtime[@]}" --env "START_ODB=$candidate/eco-routed.odb,LANDING_PATCHES=$run/repairs.tsv" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/restore_landings.tcl" > restore.log 2>&1
cmp eco-routed.v "$candidate/eco-routed.v"
"${runtime[@]}" --env "GATE_DB=$run/eco-routed.odb,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$base/gate_eco.tcl" > extraction.log 2>&1
python3 "$base/eco_load.py" "$base/../case-98099-21-7/escape-5-load.json"
python3 "$base/gate_eco.py" C "$proj" "$run/C-load.tsv"
"${runtime[@]}" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit sta-1.tcl' > sta-1.log 2>&1
