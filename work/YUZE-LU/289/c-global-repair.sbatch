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
worker() {
    mode=$1
    margin=$2
    out=$root/c-physical/global-repair-v1-${SLURM_JOB_ID}-$mode-$margin
    mkdir "$out"
    cp "$root/c-global-repair.tcl" "$out/"
    config=$root/cu/runs/C-v20-native-clock4/config.mk
    libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$config" | tail -1)
    sha256sum "$out/c-global-repair.tcl" "$config" "$root/cu/runs/C-v20-native-clock4/"{global-candidate.odb,route-source.sdc} > "$out/inputs-before.sha256"
    status=0
    srun --exclusive --nodes=1 --ntasks=1 --cpus-per-task=8 \
        /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
        --bind /public/home/yuzelu --pwd "$out" \
        --env "OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1,CU_LIBS=$libs,C_REPAIR_MARGIN=$margin,C_REPAIR_MODE=$mode" \
        /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
        /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$out/c-global-repair.tcl" > "$out/run.log" 2>&1 || status=$?
    sha256sum "$out/c-global-repair.tcl" "$config" "$root/cu/runs/C-v20-native-clock4/"{global-candidate.odb,route-source.sdc} > "$out/inputs-after.sha256"
    cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256" || status=99
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
