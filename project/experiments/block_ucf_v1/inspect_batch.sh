#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-audit
#SBATCH --partition=c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --time=UNLIMITED
#SBATCH --output=audit-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
audit="$PWD/inspect_candidate.py"
mapfile -t masks < <(python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); assert len(a)>=96; print("\n".join(",".join(map(str,a[i:i+12])) for i in range(0,96,12)))')
test $# -le 8
test $# -gt 0
pids=()
i=0
for candidate in "$@"; do
    work="$PWD/audit-$SLURM_JOB_ID-${candidate##*/}"
    mkdir -p "$work/tmp/klayout" "$work/tmp/cache"
    taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$work" --env "OMP_NUM_THREADS=12,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache" \
        "$image" bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
        bash "$audit" "$candidate" > "$work/job.log" 2>&1 &
    pids+=("$!")
    i=$((i+1))
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
