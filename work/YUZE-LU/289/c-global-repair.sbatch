#!/bin/bash
#SBATCH --job-name=yzl-289-C-loadrepair
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/c-loadrepair-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
mkdir -p "$root/c-physical"
source_dir=${C_REPAIR_SOURCE:-$root/cu/runs/C-v20-native-clock4}
source_odb=${C_REPAIR_ODB:-global-candidate.odb}
source_sdc=${C_REPAIR_SDC:-route-source.sdc}
dot_guard=${C_REPAIR_DOT_GUARD:-0}
reset_count=${C_REPAIR_RESET_COUNT:-0}
worker() {
    mode=$1
    margin=$2
    out=$root/c-physical/global-repair-v2-${SLURM_JOB_ID}-$mode-$margin
    mkdir "$out"
    cp "$root/c-global-repair.tcl" "$out/"
    cp "$root/c-target-min-delay.tcl" "$out/"
    if [ "$dot_guard" = 1 ]; then
        sha256sum "$root/cu/c-dot-actual-cut-guard-v1.tcl" "$root/audit/C-final-v1/macro-obs-v20/dot-actual-cut-obs.tsv" > "$out/dot-guard.sha256"
    fi
    config=$root/cu/runs/C-v20-native-clock4/config.mk
    libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$config" | tail -1)
    sha256sum "$out/c-global-repair.tcl" "$out/c-target-min-delay.tcl" "$config" "$source_dir/$source_odb" "$source_dir/$source_sdc" > "$out/inputs-before.sha256"
    status=0
    srun --exclusive --nodes=1 --ntasks=1 --cpus-per-task=8 \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
        --bind /public/home/yuzelu --pwd "$out" \
        --env "OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1,CU_LIBS=$libs,C_REPAIR_MARGIN=$margin,C_REPAIR_MODE=$mode,C_REPAIR_SOURCE=$source_dir,C_REPAIR_ODB=$source_odb,C_REPAIR_SDC=$source_sdc,C_REPAIR_DOT_GUARD=$dot_guard,C_REPAIR_RESET_COUNT=$reset_count,C_REPAIR_TAG=$SLURM_JOB_ID" \
        /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
        /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$out/c-global-repair.tcl" > "$out/run.log" 2>&1 || status=$?
    sha256sum "$out/c-global-repair.tcl" "$out/c-target-min-delay.tcl" "$config" "$source_dir/$source_odb" "$source_dir/$source_sdc" > "$out/inputs-after.sha256"
    cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256" || status=99
    if [ "$dot_guard" = 1 ]; then sha256sum -c "$out/dot-guard.sha256" || status=99; fi
    printf 'exit_code=%s\naccepted=false\n' "$status" > "$out/status.txt"
    return "$status"
}
if [ "$#" -eq 2 ]; then
    worker "$1" "$2"
    exit
fi
workers=()
for mode in electrical setup; do
    for margin in 0 10 20; do
        worker "$mode" "$margin" &
        workers+=("$!")
    done
done
status=0
for worker_pid in "${workers[@]}"; do
    wait "$worker_pid" || status=1
done
exit "$status"
