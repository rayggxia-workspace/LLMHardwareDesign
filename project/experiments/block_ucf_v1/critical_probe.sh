#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-crit
#SBATCH --partition=debug
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=00:15:00
#SBATCH --output=critical-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sh=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
for folder in "$@"; do
    (
    db=$(find "$folder/flow/results" -name '1_synth.odb' -print -quit)
    test -n "$db"
    name=${folder##*/}
    "$sh" exec --cleanenv --bind /public/home/yuzelu --env "ODB=$db" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit critical.tcl' > "critical-$SLURM_JOB_ID-$name.log" 2>&1
    ) &
done
wait
