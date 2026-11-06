#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-eco
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=60
#SBATCH --time=UNLIMITED
#SBATCH --output=resume-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base=$PWD
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
measured="$base/../audit-03/audit-97518-run-97498-0-1300"
cases=(1300:target 1300:target-cap60 1300:cap60 1450:cap60-hold45 1600:cap60-hold45)
mapfile -t masks < <(python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); assert len(a)>=60; print("\n".join(",".join(map(str,a[i:i+12])) for i in range(0,60,12)))')
pids=()
for i in "${!cases[@]}"; do
    IFS=: read -r side policy <<< "${cases[i]}"
    source="$base/../pnr-05/run-97498-0-$side"
    work="$base/run-$SLURM_JOB_ID-0-$side-$policy"
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
