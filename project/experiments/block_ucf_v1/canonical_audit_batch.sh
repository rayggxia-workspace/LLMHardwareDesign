#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-well
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=UNLIMITED
#SBATCH --output=canonical-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base=$PWD
budget=${SLURM_CPUS_PER_TASK:?}
test "$#" -gt 0
threads=$((budget / $#))
mapfile -t masks < <(python3 -c 'import os,sys; a=sorted(os.sched_getaffinity(0)); n,c=map(int,sys.argv[1:]); assert len(a)>=n*c; print("\n".join(",".join(map(str,a[i:i+n])) for i in range(0,n*c,n)))' "$threads" "$#")
test "${#masks[@]}" -eq "$#"
pinned=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
run_in() {
    local where=$1
    shift
    mkdir -p "$where/tmp/klayout" "$where/tmp/cache"
    taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$where" --env "SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=$threads,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$where/tmp/klayout,XDG_CACHE_HOME=$where/tmp/cache" \
        "$image" bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
        bash "$@"
}
pids=()
i=0
for candidate in "$@"; do
    case_id="well-$SLURM_JOB_ID-${candidate##*/}"
    work="$base/$case_id"
    mkdir "$work"
    (
        run_in "$work/producer" "$base/canonical_stream.py" "$candidate"
        run_in "$work/audit" "$base/inspect_candidate.py" "$work/producer"
    ) > "$work/job.log" 2>&1 &
    pids+=("$!")
    i=$((i+1))
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
