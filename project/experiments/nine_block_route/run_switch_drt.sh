#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
native="${1:?native switch directory}"
profile="${2:?c0 or nine}"
mode="${3:?placement}"
case="$repo/drt-${SLURM_JOB_ID:?}-$profile"
if [[ "$profile" == c0 ]]; then top=qwen_c0_receive; else top=qwen_nine_transport; fi
src="$repo/project/experiments/nine_block_route"
python3 -B "$src/bind_switch.py" inputs "$native/switch.lef" \
    "$native/flow/results/nangate45/$top/base/6_final.gds" "$case" "$profile" "$mode"
python3 -B "$src/switch_guides.py" "$case" "$repo/inputs" "$native/switch.lef"
cd "$case"
mkdir tmp
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:?},TMPDIR=$PWD/tmp"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
status=0
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit upper.tcl' > route.log 2>&1 || status=$?
python3 -B "$src/audit.py" "$case" > route-audit.json
exit "$status"
