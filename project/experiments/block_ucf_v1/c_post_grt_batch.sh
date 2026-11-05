#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-cpost
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=36
#SBATCH --time=UNLIMITED
#SBATCH --output=post-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
parent="$(dirname "$base")"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
mapfile -t masks < <(python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); assert len(a)>=24; print("\n".join(",".join(map(str,a[i:i+12])) for i in range(0,min(len(a),36),12) if len(a[i:i+12])==12))')
pids=()
mode="${1:-replay}"
cases=(0 1 2)
if [[ "$mode" == checkpoint ]]; then cases=(1 2); fi
for i in "${cases[@]}"; do
    skew=2
    variant=1
    if ((i > 0)); then variant=2; fi
    if ((i == 2)); then skew=3; fi
    name=run-97617-2-1500-c-skew$skew
    source="$parent/pnr-19/$name"
    audit="$parent/audit-13/audit-97657-$name"
    loads="$parent/pnr-20/loads-97663-audit-97657-$name"
    work="$base/run-$SLURM_JOB_ID-c-skew$skew-post$variant"
    mkdir -p "$work/tmp/klayout" "$work/tmp/cache"
    taskset -c "${masks[${#pids[@]}]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$work" --env "OMP_NUM_THREADS=12,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache" \
        "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
        bash "$base/resume_c_post_grt.py" "$source" "$audit" "$loads" "$variant" 12 "$mode" > "$work/job.log" 2>&1 &
    pids+=("$!")
done
fail=0
for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
exit "$fail"
