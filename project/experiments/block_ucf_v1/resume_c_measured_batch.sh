#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-cmeasured
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --time=UNLIMITED
#SBATCH --output=resume-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base=$PWD
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
source="$base/../pnr-10/run-97533-2-1500-placed-ties"
measured="$base/../audit-12/audit-97589-run-97533-2-1500-placed-ties"
mapfile -t masks < <(python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); assert len(a)>=24; print("\n".join(",".join(map(str,a[i:i+12])) for i in range(0,24,12)))')
pids=()
for i in 0 1; do
    policy="c-measured-hold$((i+1))"
    work="$base/run-$SLURM_JOB_ID-2-1500-$policy"
    mkdir -p "$work/tmp/klayout" "$work/tmp/cache"
    taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$work" --env "OMP_NUM_THREADS=12,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache" \
        "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
        bash "$base/resume_route.py" "$source" "$policy" 12 "$measured" > "$work/job.log" 2>&1 &
    pids+=("$!")
done
fail=0
for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
exit "$fail"
