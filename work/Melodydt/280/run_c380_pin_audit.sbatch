#!/usr/bin/env bash
#SBATCH --job-name=mdt-280spins
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
if [[ ${1:-} != container ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" \
       /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
       --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
       bash "$bundle/run_c380_pin_audit.sbatch" container "$SLURM_JOB_ID"
fi
source /OpenROAD-flow-scripts/env.sh
root=$base/Melodydt/runs/issue-280/gate-c380-idle-04
paired=$root/power-116935
out=$bundle/pins-$2
mkdir "$out"
sha256sum --quiet -c "$root/idle-116935/idle-results.sha256"
sha256sum --quiet -c "$paired/power-results.sha256"
for sample in mode-0 mode-1 idle-0 idle-1; do
    ref=$paired/$sample/openroad/power.tcl
    tcl=$out/$sample.tcl
    awk '/^report_activity_annotation$/{print "puts {UNANNOTATED_PINS_BEGIN}";print "report_activity_annotation -report_unannotated";print "puts {UNANNOTATED_PINS_END}";next}{print}' "$ref" > "$tcl"
    openroad -no_init -threads 2 -exit "$tcl" > "$out/$sample.log" 2>&1
    sed -n '/^UNANNOTATED_PINS_BEGIN$/,/^UNANNOTATED_PINS_END$/p' "$out/$sample.log" > "$out/$sample.pins"
    grep -E '^unannotated[[:space:]]+143$' "$out/$sample.pins"
    grep -Fx 'ACTIVITY_ANALYSIS_COMPLETED' "$out/$sample.log"
done
sha256sum "$out"/*.{tcl,log,pins} > "$out/pins-results.sha256"
sha256sum -c "$out/pins-results.sha256"
