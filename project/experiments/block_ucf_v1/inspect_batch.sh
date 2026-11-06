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
test $# -le 8
test $# -gt 0
threads=$(("${SLURM_CPUS_PER_TASK:?}" / $#))
test "$threads" -gt 0
if ((threads > 16)); then threads=16; fi
mapfile -t masks < <(python3 -c 'import os,sys; a=sorted(os.sched_getaffinity(0)); n,count=map(int,sys.argv[1:]); assert len(a)>=count*n; print("\n".join(",".join(map(str,a[i:i+n])) for i in range(0,count*n,n)))' "$threads" "$#")
test "${#masks[@]}" -eq "$#"
pids=()
i=0
extra=()
if [[ -n ${UCF_DIAGNOSTIC:-} ]]; then
    case "$UCF_DIAGNOSTIC" in
        timing-only|equivalence-only|geometry-only) extra+=("$UCF_DIAGNOSTIC") ;;
        *) exit 2 ;;
    esac
fi
for candidate in "$@"; do
    work="$PWD/audit-$SLURM_JOB_ID-${candidate##*/}"
    mkdir -p "$work/tmp/klayout" "$work/tmp/cache"
    taskset -c "${masks[i]}" "$pinned" exec --cleanenv --bind /public/home/yuzelu \
        --pwd "$work" --env "SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=$threads,OPENBLAS_NUM_THREADS=1,KLAYOUT_HOME=$work/tmp/klayout,XDG_CACHE_HOME=$work/tmp/cache,UCF_STREAM_KLAYOUT_ROOT=${UCF_STREAM_KLAYOUT_ROOT:-}" \
        "$image" bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; unset TMPDIR; exec python3 -B "$@"' \
        bash "$audit" "$candidate" "${extra[@]}" > "$work/job.log" 2>&1 &
    pids+=("$!")
    i=$((i+1))
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
